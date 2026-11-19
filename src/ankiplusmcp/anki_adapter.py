"""Narrow MCP companion client. The mechanical cards engine never imports this.

ClientSession ownership (including authenticated transport) belongs to the caller.
No credentials or raw transport exceptions are included in domain errors.
"""
import base64
import hashlib
from .coverage import ExistingNote
from .store import DomainError

OPERATIONS = frozenset({'add_note', 'update_note_fields', 'card_unsuspend', 'store_media_file'})


class AnkiAdapter:
    def __init__(self, session, *, profile: str, collection_path: str):
        if not profile or not collection_path:
            raise DomainError('CONFIG', 'Select the intended profile and collection path explicitly.')
        self.session, self.profile, self.collection_path = session, profile, collection_path

    async def capabilities(self):
        try:
            result = await self.session.list_tools()
            return frozenset(tool.name for tool in result.tools)
        except Exception:
            raise DomainError('TRANSPORT', 'Companion discovery failed; check the connection and authentication.') from None

    async def _call(self, name, arguments):
        if name not in await self.capabilities():
            raise DomainError('UNSUPPORTED', 'The connected companion lacks a required operation.')
        try:
            result = await self.session.call_tool(name, arguments)
        except Exception:
            raise DomainError('TRANSPORT', 'Companion request outcome is unknown; reconcile before any retry.') from None
        if result.isError:
            raise DomainError('COMPANION', 'Companion refused the operation; inspect state before retrying.')
        value = result.structuredContent
        if not isinstance(value, dict):
            raise DomainError('PROTOCOL', 'Companion returned no structured result.')
        return value

    async def collection_identity(self):
        value = await self._call('collection_identity', {})
        if (value.get('identity_complete') is not True or value.get('profile_name') != self.profile
                or value.get('collection_path') != self.collection_path
                or not isinstance(value.get('collection_session'), str) or not value['collection_session']
                or type(value.get('collection_created_ts')) is not int
                or not isinstance(value.get('identity_sha256'), str) or len(value['identity_sha256']) != 64):
            raise DomainError('CONFLICT', 'The selected profile binding or runtime freshness is unavailable or changed.')
        return {key:value[key] for key in ('profile_name','collection_path','collection_created_ts','identity_sha256','collection_session')}

    @staticmethod
    def _ids(ids, maximum=100):
        if not isinstance(ids, list) or len(ids)>maximum or any(type(i) is not int or i<=0 for i in ids) or len(set(ids))!=len(ids):
            raise DomainError('PROTOCOL', 'Invalid or repeated typed record IDs.')
        return ids

    async def search_notes(self, query):
        if not isinstance(query, str) or not 1<=len(query)<=2000:
            raise DomainError('LIMIT', 'Provide a bounded Anki query.')
        binding = await self.collection_identity()
        ids=[]
        while True:
            page = await self._call('find_notes', {'query':query,'limit':100,'offset':len(ids)})
            current=self._ids(page.get('noteIds'),100)
            if set(ids)&set(current) or len(ids)+len(current)>500:
                raise DomainError('LIMIT', 'Search is unstable or exceeds 500 complete notes; narrow the query.')
            ids.extend(current)
            if page.get('hasMore') is False: break
            if page.get('hasMore') is not True or not current:
                raise DomainError('PROTOCOL', 'Incomplete search pagination.')
        if await self.collection_identity()!=binding:
            raise DomainError('CONFLICT','Collection session changed during search.')
        return ids

    async def read_notes(self, note_ids):
        self._ids(note_ids,500)
        if not note_ids: return []
        binding=await self.collection_identity()
        notes=[]
        for offset in range(0,len(note_ids),100):
            batch=note_ids[offset:offset+100]
            result=await self._call('notes_info',{'notes':batch})
            rows=result.get('notes')
            if not isinstance(rows,list) or len(rows)!=len(batch) or {r.get('noteId') for r in rows}!=set(batch):
                raise DomainError('CONFLICT','A requested note is missing, repeated or foreign.')
            for row in rows:
                fields=row.get('fields')
                if not isinstance(fields,dict) or not fields or any(not isinstance(v,dict) or v.get('truncated',False) is not False or not isinstance(v.get('value'),str) for v in fields.values()):
                    raise DomainError('PROTOCOL','Complete note fields are required; excerpts cannot authorize edits.')
                cards=self._ids(row.get('cards'),500)
                notes.append(ExistingNote(note_id=row['noteId'],card_ids=cards,fields={k:v['value'] for k,v in fields.items()}))
        if len({cid for n in notes for cid in n.card_ids})!=sum(len(n.card_ids) for n in notes):
            raise DomainError('PROTOCOL','A card has conflicting note ownership.')
        if await self.collection_identity()!=binding:
            raise DomainError('CONFLICT','Collection session changed during read.')
        return notes

    async def read_cards(self, card_ids):
        self._ids(card_ids)
        if not card_ids: return []
        state=await self.operation_state('card_unsuspend',{'card_ids':card_ids})
        cards=[dict(c,note_id=n['id']) for n in state['target'] for c in n['cards'] if c['id'] in card_ids]
        if len(cards)!=len(card_ids) or {c['id'] for c in cards}!=set(card_ids) or any(c['nid']!=c['note_id'] for c in cards):
            raise DomainError('CONFLICT','Card ownership is incomplete or foreign.')
        return cards

    async def read_note_type(self, name):
        return {'fields':await self._call('model_field_names',{'model_name':name}),
                'templates':await self._call('model_templates',{'model_name':name}),
                'styling':await self._call('model_styling',{'model_name':name})}

    async def operation_state(self, operation, arguments):
        if operation not in OPERATIONS:
            raise DomainError('UNSUPPORTED','Only fixed student operations are available.')
        # Check capability before contacting a companion lacking the guard.
        if not {'student_operation_state','conditional_student_operation'} <= await self.capabilities():
            raise DomainError('UNSUPPORTED','Conditional companion operations are required.')
        binding=await self.collection_identity()
        state=await self._call('student_operation_state',{'operation':operation,'arguments':arguments})
        if state.get('version')!=1 or state.get('binding')!=binding or state.get('operation')!=operation or state.get('arguments')!=arguments or 'target' not in state:
            raise DomainError('CONFLICT','Companion state does not bind this exact request and session.')
        return state

    async def dispatch(self, operation, arguments, expected_state):
        if operation not in OPERATIONS:
            raise DomainError('UNSUPPORTED','Only fixed student operations are available.')
        if expected_state.get('binding')!=await self.collection_identity() or expected_state.get('arguments')!=arguments or expected_state.get('operation')!=operation:
            raise DomainError('CONFLICT','Reviewed operation binding changed.')
        return await self._call('conditional_student_operation',{'operation':operation,'arguments':arguments,'expected_state':expected_state})

    async def read_media(self, filename):
        result=await self._call('read_media_file',{'filename':filename})
        try: data=base64.b64decode(result['data'],validate=True)
        except (KeyError,ValueError,TypeError):
            raise DomainError('PROTOCOL','Invalid media byte readback.') from None
        if len(data)>8*1024*1024 or result.get('filename')!=filename or result.get('size')!=len(data) or result.get('sha256')!=hashlib.sha256(data).hexdigest():
            raise DomainError('PROTOCOL','Media content verification failed.')
        return result

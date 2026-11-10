"""Reviewers write what comes naturally; the parser keeps the signal and drops what cannot apply."""
import pytest

from cards.common.errors import CardsError
from cards.review import parse_report

FIELDS = {'n001': {'Text': 'x {{c1::a}} {{c2::b}}', 'Extra': ''}}


def student(tmp_path, attempt):
    path = tmp_path / 'student_report.md'
    path.write_text('# Review Report — anki-student\n\n## Note n001 — PASS\n'
                    f'**Attempt:** {attempt}\n\n## Summary\n**Verdict:** PASS\n**Stats:** cards=1\n')
    return parse_report.parse(path, 'student', {'n001'}, FIELDS)[0]['attempt']


def maintainer(tmp_path, rewrite):
    path = tmp_path / 'maintainer_report.md'
    path.write_text('# Review Report — anki-maintainer\n\n## Note n001 — FIX — A3\n**Evidence:** e\n'
                    f'{rewrite}\n\n## Summary\n**Verdict:** PASS_WITH_FIXES\n**Stats:** notes=1\n')
    return parse_report.parse(path, 'maintainer', {'n001'}, FIELDS)[0]


def test_single_attempt_keeps_its_answer(tmp_path):
    assert student(tmp_path, 'my answer → right') == {'answer': 'my answer', 'result': 'right'}


def test_per_cloze_attempts_take_the_worst_result(tmp_path):
    attempt = student(tmp_path, 'c1 a → right; c2 b → alternative; c3 c → unknowable')
    assert attempt['result'] == 'alternative'
    assert student(tmp_path, 'c1 a → right; c2 b → unknowable')['result'] == 'unknowable'
    assert student(tmp_path, 'c1 a → right; c2 b → right')['result'] == 'right'


def test_attempt_may_carry_trailing_commentary(tmp_path):
    attempt = student(tmp_path, 'c1 flexion → right (the front helps); c2 x → right. Low yield.')
    assert attempt['result'] == 'right'
    assert student(tmp_path, 'c1 spine → right (partial)')['result'] == 'right'


def test_attempt_without_a_result_is_still_refused(tmp_path):
    with pytest.raises(CardsError) as error:
        student(tmp_path, 'c1 a; c2 b')
    assert 'attempt' in str(error.value)


def test_rewrite_objective_and_tags_are_ignored(tmp_path):
    row = maintainer(tmp_path, '**Rewrite Text:** `y {{c1::a}}`\n**Rewrite objective:** ILO1\n'
                               '**Rewrite tags:** `#ColdRecall::^Subjects::Anatomy`')
    assert row['rewrite'] == {'Text': 'y {{c1::a}}'}


def test_substantive_foreign_field_requires_reviewer_repair(tmp_path):
    with pytest.raises(CardsError):
        maintainer(tmp_path, '**Rewrite Text:** `y {{c1::a}}`\n**Rewrite Back Extra:** `<div>s</div>`')


def test_a_misspelt_rewrite_field_is_still_refused(tmp_path):
    with pytest.raises(CardsError) as error:
        maintainer(tmp_path, '**Rewrite Txt:** `y`')
    assert 'rewrite fields' in str(error.value)


def test_stats_with_parenthetical_annotations_are_tolerated(tmp_path):
    path = tmp_path / 'student_report.md'
    path.write_text('# Review Report — anki-student\n\n## Note n001 — FIX — V6 (blocker)\n**Attempt:** answer → right\n\n## Summary\n**Verdict:** PASS_WITH_FIXES\n**Stats:** cards=80, notes=44, attempts_right=78, alternatives=1 (n019), blockers=4 (n019 V2)\n')
    rows = parse_report.parse(path, 'student', {'n001'}, {'n001': {'Text': 'x'}})
    assert rows[-1]['stats'] == {'cards': 80, 'notes': 44, 'attempts_right': 78, 'alternatives': 1, 'blockers': 4}


def test_affected_notes_allow_separate_commentary(tmp_path):
    path = tmp_path / 'maintainer_report.md'
    path.write_text('# Review Report — anki-maintainer\n'
                    '## Set Finding — S1\n'
                    '**Notes affected:** `n001`; AnKing notes cover this fact\n'
                    '**Finding:** overlap\n**Fix:** reconcile\n'
                    '## Summary\n**Verdict:** PASS_WITH_FIXES\n**Stats:** notes=1\n')
    rows = parse_report.parse(path, 'maintainer', {'n001'}, FIELDS)
    assert rows[0]['notes'] == ['n001']


def test_unknown_affected_note_is_still_refused(tmp_path):
    path = tmp_path / 'maintainer_report.md'
    path.write_text('# Review Report — anki-maintainer\n'
                    '## Set Finding — S1\n**Notes affected:** n999; commentary\n'
                    '**Finding:** overlap\n**Fix:** reconcile\n'
                    '## Summary\n**Verdict:** FAIL\n**Stats:** notes=1\n')
    with pytest.raises(CardsError):
        parse_report.parse(path, 'maintainer', {'n001'}, FIELDS)


def test_semicolon_cannot_silently_drop_an_affected_note(tmp_path):
    path = tmp_path / 'maintainer_report.md'
    path.write_text('# Review Report — anki-maintainer\n'
                    '## Set Finding — S1\n**Notes affected:** n001; n002\n'
                    '**Finding:** overlap\n**Fix:** reconcile\n'
                    '## Summary\n**Verdict:** FAIL\n**Stats:** notes=2\n')
    with pytest.raises(CardsError):
        parse_report.parse(path, 'maintainer', {'n001', 'n002'}, FIELDS)


def test_summary_stats_do_not_absorb_closing_commentary(tmp_path):
    path = tmp_path / 'student_report.md'
    path.write_text('# Review Report — anki-student\n'
                    '## Note n001 — PASS\n**Attempt:** answer → right\n'
                    '## Summary\n**Verdict:** PASS_WITH_FIXES\n'
                    '**Stats:** cards=114, attempts_right=111, alternatives=3\n\n'
                    'The three V2 alternatives require maintainer A2 review.\n')
    rows = parse_report.parse(path, 'student', {'n001'}, FIELDS)
    assert rows[-1]['stats'] == {'cards': 114, 'attempts_right': 111, 'alternatives': 3}


def test_malformed_stats_value_is_not_hidden_as_commentary(tmp_path):
    path = tmp_path / 'student_report.md'
    path.write_text('# Review Report — anki-student\n'
                    '## Note n001 — PASS\n**Attempt:** answer → right\n'
                    '## Summary\n**Verdict:** PASS\n**Stats:** cards=many\n')
    with pytest.raises(CardsError):
        parse_report.parse(path, 'student', {'n001'}, FIELDS)

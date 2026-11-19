"""Disposable packaged companion, same-thread dispatch over stdio only."""
from contextlib import redirect_stdout
import importlib
from pathlib import Path
import shutil
import sys
from types import SimpleNamespace
import aqt
from anki.collection import Collection

root=Path(sys.argv[1]).resolve();name=sys.argv[2]
assert root.is_relative_to(Path('/tmp')) and root.name.startswith('student-product-')
shutil.copytree('/artifact/addon',root/name);sys.path.insert(0,str(root))
col=Collection(str(root/'collection.anki2'))
try:
    aqt.mw=SimpleNamespace(col=col,pm=SimpleNamespace(name='Synthetic'),addonManager=SimpleNamespace(getConfig=lambda name:{}))
    with redirect_stdout(sys.stderr):
        importlib.import_module(name)
        registry=importlib.import_module(name+'.handler_registry')
        primitives=importlib.import_module(name+'.primitives')
        importlib.import_module(name+'.collection_session').begin()
        from mcp.server.fastmcp import FastMCP
        server=FastMCP('local-synthetic-companion')
        async def dispatch(tool,args):return registry.execute(tool,args)
        primitives.register_all_tools(server,dispatch)
    server.run(transport='stdio')
finally:col.close()

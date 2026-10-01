from __future__ import annotations
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

USER_AGENT='bist-research-terminal/0.2'
def robots_allowed(url:str,fetcher=None)->bool|None:
    p=urlparse(url); robots=f'{p.scheme}://{p.netloc}/robots.txt'
    try:
        rp=RobotFileParser(robots)
        if fetcher is None: rp.read()
        else: rp.parse(fetcher(robots).splitlines())
        return rp.can_fetch(USER_AGENT,url)
    except Exception:
        return None

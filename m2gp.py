#!/usr/bin/env python3
# coding: utf-8
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
r"""https://github.com/vbem/man-to-github-pages
"""
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
__all__     = []
__version__ = (0, 1, 0, 'alpha', 0)
__author__  = 'vbem <i@lilei.tech>'
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
import os
import sys
import re
import argparse
import logging
import subprocess
import functools
import operator
import textwrap
import itertools
import html
import queue
import threading
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
LOG = logging.getLogger(__name__)
LOG_FMT_DEMO = '[%(asctime)s %(levelname)s %(name)s %(module)s:%(funcName)s:%(lineno)d] %(message)s'
LOG_HANDLER_DEMO = logging.StreamHandler()
LOG_HANDLER_DEMO.setFormatter(logging.Formatter(LOG_FMT_DEMO))
LOG.addHandler(LOG_HANDLER_DEMO) # as app
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

def reprArgs(*t, **d):
    r'''Return arguments' representation string as in scrpit's function invocation.
    '''
    return '({})'.format(', '.join(itertools.chain( # chain generators, then join with comma, finally enclosed
        (repr(arg) for arg in t),   # Generator of positional arguments
        ('{}={!r}'.format(*tKv) for tKv in d.items()), # Generator of keyword arguments
    )))

def getFuncFullName(func):
    r'''Return `package-name.module-name.class-name.method-name` like qualified name of given function object.
    '''
    if not callable(func):
        raise TypeError('{func!r} is not callable'.format_map(locals()))
    return '{}.{}'.format(func.__module__, func.__qualname__)

def decorateLog(logger, nLevel=logging.DEBUG):
    r'''A decorator wraps longging on function call's begin and end with given logger and level.
    '''
    if not isinstance(logger, logging.Logger):
        raise TypeError('{logger!r} is not a logging.Logger instance'.format_map(locals()))
    if nLevel not in logging._levelToName:
        raise ValueError('{nLevel!r} is not a valid logging level'.format_map(locals()))

    def decorator(func):
        sFunc = getFuncFullName(func)

        @functools.wraps(func)
        def wrapper(*t, **d):
            nonlocal sFunc
            sArgs = reprArgs(*t, **d)
            logger.log(nLevel, '%(sFunc)s <= %(sArgs)s', locals())
            try:
                result = func(*t, **d)
            except BaseException as e:
                logger.log(nLevel, '%(sFunc)s raises %(e)r', locals())
                raise
            else:
                logger.log(nLevel, '%(sFunc)s => %(result)r', locals())
                return result

        return wrapper

    return decorator

def shrink(s):
    r"""Shrink a text by `textwrap.detent` and then `str.strip`.
    """
    if not isinstance(s, str):
        raise TypeError('{s!r} is not str type'.format_map(locals()))
    return textwrap.dedent(s).strip()

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
class ManManager:
    r'''Manager for man-pages.
    '''

    PATTERN_APROPOS = re.compile(r'''^
        (?P<name>.+)
        \s
        \((?P<section>.+)\)
        \s+-\s
        (?P<description>.+)
    $''', re.VERBOSE | re.IGNORECASE)

    TPL_INDEX_BEGIN = shrink('''
    <html>
    <head><title>Man Pages on Github Pages</title></head>
    <body bgcolor="white">
    <h1><a href="https://github.com/vbem/man-to-github-pages" target="_blank">Man Pages on Github Pages</a></h1>
    Use CTRL+F for searching.<br />
    For more, check <a href="http://man7.org/linux/man-pages/index.html" target="_blank">man7.org</a> and <a href="http://linux.die.net/man/"   target="_blank">die.net</a>.
    <hr><table border="1">
    <tr><td>Section</td><td>Name</td><td>Description</td></tr>
    ''')

    TPL_INDEX_END = shrink('''
    </table><hr></body>
    </html>
    ''')

    TPL_MAN_PATH = 'man/{sSection}_{sName}.html'

    @decorateLog(LOG)
    def __init__(self, *t, **d):
        r'''Initilization.
        '''
        super().__init__(*t, **d)

    @decorateLog(LOG)
    def updateIndex(self):
        r'''Update Index from man-pages database.
        '''
        self._lIndex = []
        with subprocess.Popen(('man','-k', ''), stdout=subprocess.PIPE, universal_newlines=True) as popenApropos:
            for sLine in popenApropos.stdout:
                match = self.__class__.PATTERN_APROPOS.match(sLine)
                if not match:
                    LOG.warning('line %r does not match', sLine)
                    continue
                self._lIndex.append((match.group('name'), match.group('section'), match.group('description')))
        return len(self._lIndex)

    @decorateLog(LOG)
    def sortIndex(self, tSequence=(1,0,2)):
        r'''Sort Index.
        '''
        self._lIndex.sort(key=operator.itemgetter(*tSequence))

    def _yieldIndexHtmlLine(self):
        r'''Yield index.html line.
        '''
        yield self.__class__.TPL_INDEX_BEGIN
        for sName, sSection, sDescription in self._lIndex:
            sName = html.escape(sName)
            sSection = html.escape(sSection)
            sDescription = html.escape(sDescription)
            sPath = html.escape(self.__class__.TPL_MAN_PATH.format_map(locals()))
            yield "<tr><td>{sSection}</td><td><a href='{sPath}' target='_blank'>{sName}</a></td><td>{sDescription}</td></tr>\n".format_map(locals())
        yield self.__class__.TPL_INDEX_END

    @decorateLog(LOG)
    def writeIndexHtml(self):
        r'''Write index.html.
        '''
        with open('index.html', 'w') as f:
            for sLine in self._yieldIndexHtmlLine():
                f.write(sLine)

    def _getManHtml(self, sName, sSection):
        r'''Get man-page HTML.
        '''
        completed = subprocess.run(['man', '-Thtml', sSection, sName], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        if completed.returncode:
            LOG.warning('return code %s for name %r in section %r', completed.returncode, sName, sSection)
        return completed.stdout

    @decorateLog(LOG)
    def writeManHtml(self):
        r'''Write man-page HTML files.
        '''
        for (n, (sName, sSection, _)) in enumerate(self._lIndex, 1):
            sHtml = self._getManHtml(sName, sSection)
            sPath = self.__class__.TPL_MAN_PATH.format_map(locals())
            with open(sPath, 'w') as f:
                f.write(sHtml)
            LOG.info('%r generated, %s/%s', sPath, n, len(self._lIndex))

    @decorateLog(LOG)
    def writeManHtmlWithThreading(self):
        r'''Write man-page HTML files with multi threading.
        '''
        nThreadsSize = os.cpu_count() * 2 + 1

        self._qInput = queue.Queue()
        for n, (sName, sSection, _) in enumerate(self._lIndex, 1):
            self._qInput.put((n, sName, sSection))
        for n in range(nThreadsSize):
            self._qInput.put(EOFError)
        LOG.debug('built queue')

        lThreads = [
            threading.Thread(target=self._target_writeManHtml, name='_target_writeManHtml-{}/{}'.format(n+1, nThreadsSize))
            for n in range(nThreadsSize)
        ]
        LOG.debug('built threads list size %s', nThreadsSize)
        for thread in lThreads:
            thread.start()
        LOG.debug('all threads start')

        for thread in lThreads:
            thread.join()
        LOG.debug('all threads join')

    def _target_writeManHtml(self):
        while True:
            fetch = self._qInput.get()
            if fetch is EOFError:
                LOG.debug('{} terminated'.format(threading.current_thread().name))
                break
            n, sName, sSection = fetch
            sHtml = self._getManHtml(sName, sSection)
            sPath = self.__class__.TPL_MAN_PATH.format_map(locals())
            with open(sPath, 'w') as f:
                f.write(sHtml)
            LOG.info('%s generated %r, %s/%s', threading.current_thread().name, sPath, n, len(self._lIndex))

    @decorateLog(LOG)
    def buildHtml(self):
        r'''Build HTML files.
        '''
        n = self.updateIndex()
        LOG.info('found %s man-page names', n)
        self.sortIndex()
        self.writeIndexHtml()
        LOG.info("'index.html' generated")
        self.writeManHtmlWithThreading()

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# CLI functions

def runCli(lCliArgs=None):
    r'''Run CLI.
    '''
    dCommonParserInitArgs = {
        'formatter_class' : argparse.RawTextHelpFormatter,
        'epilog' : 'I/O: stdin->input, stdout->result, stderr->logging, exit code->status check',
    }

    s = shrink(__doc__)
    parserMain = argparse.ArgumentParser(description=s, **dCommonParserInitArgs)
    groupMutex = parserMain.add_mutually_exclusive_group()
    s = 'disable all logging messages'
    groupMutex.add_argument('-q', '--quite', action='store_true', help=s)
    s = shrink(r"""
        increase logging verbosity
        without this, log at `warning` level
        with `-v`, log at `info` level
        with `-vv`, log at `debug` level
    """)
    groupMutex.add_argument('-v', '--verbose', action='count', default=0, help=s)

    s = 'each sub-command for a specific task'
    actionSub = parserMain.add_subparsers(dest='subcommand', description=s)

    s = 'build all man-pages to HTML files'
    parserBuild = actionSub.add_parser(name='build', description=s, help=s, **dCommonParserInitArgs)

    s = 'show docs in source code'
    parserDocs = actionSub.add_parser(name='docs', description=s, help=s, **dCommonParserInitArgs)

    namespace = parserMain.parse_args(args=lCliArgs)

    if namespace.quite:
        LOG.setLevel(51)
    else:
        LOG.setLevel(logging.WARNING if namespace.verbose==0 else logging.INFO if namespace.verbose==1 else logging.DEBUG)

    LOG.debug(namespace)

    if not namespace.subcommand:
        LOG.warning('no sub-command specified, show help instead')
        parserMain.print_help()
        return 1

    if namespace.subcommand == 'docs':
        help(os.path.splitext(os.path.basename(__file__))[0])
        return 0

    if namespace.subcommand == 'build':
        m = ManManager()
        m.buildHtml()
        return 0

    return 255

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
if __name__ == "__main__":
    nRet = runCli()
    LOG.info('terminates with status code: {nRet}'.format_map(locals()))
    sys.exit(nRet)


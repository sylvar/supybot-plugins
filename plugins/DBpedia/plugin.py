
import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks

from lxml import etree
from StringIO import StringIO
import supybot.utils.web as web
from urllib import urlencode

import rdflib

HEADERS = dict(ua = 'Zoia/1.0 (Supybot/0.83; DBPedia Plugin; http://code4lib.org/irc)')
SERVICE_URL = 'http://lookup.dbpedia.org/api/search.asmx/KeywordSearch?QueryClass=String&MaxHits=10&%s'
NSMAP = {'ns':'http://lookup.dbpedia.org/'}

class DBpedia(callbacks.Plugin):
    """Methods for searching DBpedia"""
    threaded = True

    def uri(self, irc, msg, args, term):
        """
        find the most-likely DBpedia URIs for a given keyword(s)
        """
        results = self._search(term)
        if not len(results):
            irc.reply("no matches :(")
            return
        resp = '; '.join([ "%s - %s" % (c,u) for l,c,u in results])
        irc.reply("DBpedia has URIs for... %s" % resp)

    uri = wrap(uri, ['text'])

    def describe(self, irc, msg, args, uri):
        """print out some extracted text for a given RDF resource URI
        """
        try:
            parts = self._describe(uri)
            if len(parts) > 0:
                irc.reply('; '.join(parts).encode('utf-8'))
            else:
                irc.reply('sorry something went wrong, i am a strange hack')
        except Exception, e:
            irc.reply(str(u))
          

    describe = wrap(describe, ['text'])

    def uris(self, irc, msg, args, uri):
        """find other URIs for a given resource using owl:sameAs, rdfs:seeAlso 
        """
        sameas = []
        try:
            g = rdflib.ConjunctiveGraph()
            g.load(uri)
            for s, p, o in g:
                if p in (rdflib.URIRef("http://www.w3.org/2002/07/owl#sameAs"),
                         rdflib.RDFS.seeAlso):
                    sameas.append(o)

        except:
            pass # uhoh
        if len(sameas) > 0:
            irc.reply("more info about %s can be found at: %s" % (uri, ', '.join(sameas)))
        else:
            irc.reply('no equivalent resources found')

    uris = wrap(uris, ['text'])

    def whatis(self, irc, msg, args, term):
        """does a search in dbpedia and extracts the description for the first
        hit
        """
        results = self._search(term)
        if len(results) >= 1:
            uri = results[0][2]
            parts = self._describe(uri)
            desc = '; '.join(parts)
            irc.reply(('<%s> %s' % (uri, desc)).encode('utf-8'))
        else:
            irc.reply('better luck next time')

    whatis = wrap(whatis, ['text'])

    def _search(self, term):
        xml = web.getUrl(SERVICE_URL % urlencode({ 'QueryString': term }), headers=HEADERS)
        parser = etree.XMLParser(ns_clean=True, remove_blank_text=True)
        tree = etree.parse(StringIO(xml), parser)
        results = []
        for r in self._xpath(tree, '//ns:Result'):
            label = self._xpath(r, 'ns:Label/text()', 0)
            uri = self._xpath(r, 'ns:URI/text()', 0)
            category = self._xpath(r, 'ns:Categories/ns:Category/ns:Label/text()', 0)
            results.append((label,category,uri))
        return results

    def _xpath(self, node, expr, idx=None):
        res = node.xpath(expr, namespaces=NSMAP)
        if idx is None:
            return res
        else:
            try:
                return res[idx]
            except IndexError:
                return None

    def _describe(self, uri):
        g = rdflib.ConjunctiveGraph()
        g.load(uri)
        parts = []
        for s, p, o in g:
            if type(o) == rdflib.Literal:
                if o.language and o.language != 'en':
                    continue
                if '#' in p:
                    label = p.split('#')[-1]
                else:
                    label = p.split('/')[-1]
                parts.append("%s: %s" % (label, o))
        return parts

Class = DBpedia


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

#!/usr/bin/env python

import re
import json
import rdflib
import urlparse
import lxml.html

def main():
    saa = {}
    for t in terms():
        print t['pref_label']
        saa[t['pref_label']] = t
    open("saa-glossary.json", "w").write(json.dumps(saa, indent=2))

def terms():
    for url in term_urls():
        t = term(url)
        if t: yield t

def term_urls():
    doc = lxml.html.parse('http://www.archivists.org/glossary/list.asp')
    for a in doc.xpath('.//a'):
        href = a.attrib['href']
        if href.startswith('term_details.asp'):
            yield urlparse.urljoin("http://www.archivists.org/glossary/", href)

def term(url):
    term = {
        'url': url, 
        'pref_label': None, 
        'definition': None,
        'alt_label': [], 
        'broader': [],
        'narrower': [],
        'related': [],
        'distinguish_from': [],
        'notes': [],
        'citations': []
        }
    doc = lxml.html.parse(url)
    term['pref_label'] = doc.find('.//h2').text
    for p in doc.xpath(".//p[@class='head']"):
        if p.text.startswith("Definition"):
            definition = p.getnext().find('p')
            text = definition.text_content()
            if text.startswith("(also"):
                for alt_label in definition.findall('span'):
                    term['alt_label'].append(alt_label.text_content())
                html = lxml.html.tostring(definition)
                html = re.sub("^.+</span>\), ", "", html)
                definition = lxml.html.fromstring(html)
                term['definition'] = definition.text_content()
            elif "abbr.)" in text:
                m = re.match('^(.+) \((.+), abbr.\)(.+)$', text)
                if m:
                    term['alt_label'].append(m.group(2))
                    term['definition'] = m.group(1) + m.group(3)
            else:
                term['definition'] = definition.text_content()
        if p.text.startswith("Notes"):
            for note in p.getnext().findall('.//p'):
                if note.text: term['notes'].append(note.text)
        if p.text.startswith("Citations"):
            for cite in p.getnext().findall('.//p/a'):
                c = citation(cite)
                if c: term['citations'].append(c)

    term['broader'] = syndetic_links(doc, "BT:", url)
    term['related'] = syndetic_links(doc, "RT:", url)
    term['distinguish_from'] = syndetic_links(doc, "DF:", url)
    term['narrower'] = syndetic_links(doc, "NT:", url)

    # some pages are just See links to the actual terms
    if term['definition'] and not term['definition'].startswith('(also'):
        return term
    else:
        return None

def syndetic_links(doc, label, url):
    links = []
    for td in doc.findall(".//td[@class='syndetic']"):
        if td.text != label: continue
        for a in td.getnext().findall('a'):
            links.append({
                'pref_label': a.text, 
                'url': urlparse.urljoin(url, a.attrib['href'])
                })
    return links 

def citation(cite):
    url = urlparse.urljoin('http://www.archivists.org/glossary/', cite.attrib['href'])
    doc = lxml.html.parse(url)
    dt = doc.find('.//dl/dt')
    if dt == None: return
    author = dt.text
    source = ' '.join([e.text_content() for e in doc.findall('.//dl/dd')])
    return {
      "quotation": cite.tail,
      "author": author,
      "source": source,
      "url": url
      }

if __name__ == "__main__":
    main()
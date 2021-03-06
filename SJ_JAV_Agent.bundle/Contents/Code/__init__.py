# -*- coding: utf-8 -*-
import urllib
import os
import re
import unicodedata

def Start(): 
    HTTP.CacheTime = 0
    HTTP.Headers['Accept'] = 'text/html, application/json'

def change_html(str):
    return str.replace('&nbsp;', ' ').replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&').replace('&quot;', '"').replace('&#35;', '#').replace('&#39;', "‘")

class SJ_JAV_Agent(Agent.Movies):
    name = "SJVA AV"
    languages = [Locale.Language.Korean]
    primary_provider = True
    accepts_from = ['com.plexapp.agents.localmedia', 'com.plexapp.agents.xbmcnfo']
    contributes_to = [
        'com.plexapp.agents.xbmcnfo',
    ]

    def search(self, results, media, lang, manual=False):
        Log('SEARCH : %s %s %s' % (media.name, media.year, media.id)) 
        #search_name = media.name
        #if len(media.name.split(' ')) == 1:
        if manual:
            search_name = unicodedata.normalize('NFKC', unicode(media.name)).strip()
        else:
            url = 'http://127.0.0.1:32400/library/metadata/%s' % media.id
            data = JSON.ObjectFromURL(url)
            Log(data) 
            filename = data['MediaContainer']['Metadata'][0]['Media'][0]['Part'][0]['file']
            search_name = os.path.splitext(os.path.basename(filename))[0].replace('-', ' ')
        data = self.search2(results, media, lang, search_name)
        if not data:
            # western 만
            match = Regex(r'\.\d{2}\.\d{2}.\d{2}').search(search_name)
            if match:
                search_name = os.path.splitext(os.path.basename(os.path.dirname(filename)))[0].replace('-', ' ')
                self.search2(results, media, lang, search_name)

    def search2(self, results, media, lang, search_name):
        search_name = re.sub('\s*\[.*?\]', '', search_name).strip()
        match = Regex(r'(?P<cd>cd\d{1,2})$').search(search_name) 
        if match:
            search_name = search_name.replace(match.group('cd'), '')
        #url = '%s/av_agent/api/search?code=%s&content_type=%s&apikey=%s' % (Prefs['server'], urllib.quote(search_name.encode('utf8')), content_type, Prefs['apikey'])
        url = '%s/av_agent/api/search?code=%s&apikey=%s' % (Prefs['server'], urllib.quote(search_name.encode('utf8')), Prefs['apikey'])
        data = JSON.ObjectFromURL(url, timeout=int(Prefs['timeout']))
        Log('DATA %s' % data)
        for item in data:
            title = '[%s]%s' % (item['id_show'], String.DecodeHTMLEntities(String.StripTags(item['title_ko'])).strip())
            id = item['id']
            score = int(item['score'])
            year = media.year
            Log.Debug('ID=%s, media.name=%s, title=%s, year=%s, score=%d' %(id, search_name, title, year, score))
            results.Append(MetadataSearchResult(id=id, name=title, year=year, score=score, lang=lang))
        return data

    def update(self, metadata, media, lang):
        Log("UPDATE : %s" % metadata.id)
        url = '%s/av_agent/api/update?code=%s&apikey=%s' % (Prefs['server'], metadata.id, Prefs['apikey'])
        data = JSON.ObjectFromURL(url, timeout=int(Prefs['timeout']))
        if data['code_show'] != '':
            metadata.title = '[%s]%s' % (data['code_show'], change_html(data['title_ko']))
        else:
            metadata.title = '%s' % (change_html(data['title_ko']))
        metadata.original_title = change_html(data['title'])
        metadata.title_sort = '%s' % data['code_show']
        try: metadata.year = int(data['date'][0:4])
        except: pass
        try: metadata.rating = float(data['rating']) * 2
        except: pass
        metadata.genres.clear()
        for item in data['genre']: 
            metadata.genres.add(item)
        try: metadata.duration = int(data['running_time'])*60
        except: pass
        try: metadata.originally_available_at = Datetime.ParseDate(data['date']).date()
        except: pass
        metadata.summary = change_html(String.DecodeHTMLEntities(String.StripTags(data['summary_ko']).strip()).split(u'※')[0])
        metadata.studio = change_html(data['studio_ko'])
        metadata.collections.clear()
        if Prefs['use_collection_release'] and data['release'] != '':
            metadata.collections.add('[%s]' % data['release'].upper())
        if Prefs['use_collection_series'] and data['series_ko'] != '':
            metadata.collections.add(change_html(data['series_ko']))
        if Prefs['use_collection_label'] and data['label_ko'] != '':
            metadata.collections.add(change_html(data['label_ko']))
        try: metadata.posters[data['poster']] = Proxy.Preview(HTTP.Request( data['poster'] ))
        except: pass
        metadata.roles.clear()
        for item in data['performer']:
            meta_role = metadata.roles.new()
            meta_role.role = item['name']
            meta_role.name = item['name_kor'] if item['name_kor'] != '' else item['name']
            meta_role.photo = item['img']
        metadata.directors.clear()
        if data['director_ko'] != '':
            meta_director = metadata.directors.new()
            meta_director.name = data['director_ko']
        idx_art = 0
        try: max = int(Prefs['max_num_arts'])
        except: max = 100
        for item in data['sample_image']:
            try: metadata.art[item['full']] = Proxy.Preview(HTTP.Request(item['full']), sort_order = idx_art)
            except: pass
            idx_art += 1
            if idx_art >= max: break
        if data['poster_full'] != '':
            try: metadata.art[data['poster_full']] = Proxy.Preview(HTTP.Request(data['poster_full']), sort_order = idx_art)
            except: pass
        

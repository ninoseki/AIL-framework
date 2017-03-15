#!/usr/bin/env python2
# -*-coding:UTF-8 -*

'''
    Flask functions and routes for the trending modules page
'''
import redis
import json
import os
import flask
from flask import Flask, render_template, jsonify, request

import Paste

# ============ VARIABLES ============
import Flask_config

app = Flask_config.app
cfg = Flask_config.cfg
r_serv_pasteName = Flask_config.r_serv_pasteName
max_preview_char = Flask_config.max_preview_char
max_preview_modal = Flask_config.max_preview_modal


baseindexpath = os.path.join(os.environ['AIL_HOME'], cfg.get("Indexer", "path"))
indexRegister_path = os.path.join(os.environ['AIL_HOME'], 
                         cfg.get("Indexer", "register"))

# ============ FUNCTIONS ============
def get_current_index():
    with open(indexRegister_path, "r") as f:
        allIndex = f.read()
        allIndex = allIndex.split(',')
        allIndex.sort()
        indexnum = int(allIndex[-1])
        indexpath = os.path.join(baseindexpath, "index_"+str(indexnum))
    return indexpath

def get_index_list(selected_index=""):
    index_list = []
    for dirs in os.listdir(baseindexpath):
        if os.path.isdir(os.path.join(baseindexpath, dirs)):
            index_list.append([ dirs, dirs + " - " + str(get_dir_size(dirs) / (1000*1000)) + " Mb", dirs==selected_index.split('/')[-1]])
    return index_list

def get_dir_size(directory):
    cur_sum = 0
    for directory, subdirs, files in os.walk(os.path.join(baseindexpath,directory)):
        cur_sum += sum(os.path.getsize(os.path.join(directory, name)) for name in files)
    return cur_sum


# ============ ROUTES ============

@app.route("/search", methods=['POST'])
def search():
    query = request.form['query']
    q = []
    q.append(query)
    r = [] #complete path
    c = [] #preview of the paste content
    paste_date = []
    paste_size = []
    index_num = request.form['index_num']
    num_elem_to_get = 50

    # select correct index
    if index_num is None or index_num == "0":
        selected_index = get_current_index()
    else:
        selected_index = os.path.join(baseindexpath, index_num)

    # Search filename
    for path in r_serv_pasteName.smembers(q[0]):
        r.append(path)
        paste = Paste.Paste(path)
        content = paste.get_p_content().decode('utf8', 'ignore')
        content_range = max_preview_char if len(content)>max_preview_char else len(content)-1
        c.append(content[0:content_range])
        curr_date = str(paste._get_p_date())
        curr_date = curr_date[0:4]+'/'+curr_date[4:6]+'/'+curr_date[6:]
        paste_date.append(curr_date)
        paste_size.append(paste._get_p_size())

    # Search full line
    from whoosh import index
    from whoosh.fields import Schema, TEXT, ID
    schema = Schema(title=TEXT(stored=True), path=ID(stored=True), content=TEXT)

    ix = index.open_dir(selected_index)
    from whoosh.qparser import QueryParser
    with ix.searcher() as searcher:
        query = QueryParser("content", ix.schema).parse(" ".join(q))
        results = searcher.search_page(query, 1, pagelen=num_elem_to_get)
        for x in results:
            r.append(x.items()[0][1])
            paste = Paste.Paste(x.items()[0][1])
            content = paste.get_p_content().decode('utf8', 'ignore')
            content_range = max_preview_char if len(content)>max_preview_char else len(content)-1
            c.append(content[0:content_range])
            curr_date = str(paste._get_p_date())
            curr_date = curr_date[0:4]+'/'+curr_date[4:6]+'/'+curr_date[6:]
            paste_date.append(curr_date)
            paste_size.append(paste._get_p_size())
        results = searcher.search(query)
        num_res = len(results)

    index_min = 1
    index_max = len(get_index_list())
    return render_template("search.html", r=r, c=c, 
            query=request.form['query'], paste_date=paste_date, 
            paste_size=paste_size, char_to_display=max_preview_modal, 
            num_res=num_res, index_min=index_min, index_max=index_max,
            index_list=get_index_list(selected_index)
           )


@app.route("/get_more_search_result", methods=['POST'])
def get_more_search_result():
    query = request.form['query']
    q = []
    q.append(query)
    page_offset = int(request.form['page_offset'])
    index_num = request.form['index_num']
    num_elem_to_get = 50

    # select correct index
    if index_num is None or index_num == "0":
        selected_index = get_current_index()
    else:
        selected_index = os.path.join(baseindexpath, index_num)

    path_array = []
    preview_array = []
    date_array = []
    size_array = []

    from whoosh import index
    from whoosh.fields import Schema, TEXT, ID
    schema = Schema(title=TEXT(stored=True), path=ID(stored=True), content=TEXT)

    ix = index.open_dir(selected_index)
    from whoosh.qparser import QueryParser
    with ix.searcher() as searcher:
        query = QueryParser("content", ix.schema).parse(" ".join(q))
        results = searcher.search_page(query, page_offset, num_elem_to_get)   
        for x in results:
            path_array.append(x.items()[0][1])
            paste = Paste.Paste(x.items()[0][1])
            content = paste.get_p_content().decode('utf8', 'ignore')
            content_range = max_preview_char if len(content)>max_preview_char else len(content)-1
            preview_array.append(content[0:content_range])
            curr_date = str(paste._get_p_date())
            curr_date = curr_date[0:4]+'/'+curr_date[4:6]+'/'+curr_date[6:]
            date_array.append(curr_date)
            size_array.append(paste._get_p_size())
        to_return = {}
        to_return["path_array"] = path_array
        to_return["preview_array"] = preview_array
        to_return["date_array"] = date_array
        to_return["size_array"] = size_array
        if len(path_array) < num_elem_to_get: #pagelength
            to_return["moreData"] = False
        else:
            to_return["moreData"] = True

    return jsonify(to_return)



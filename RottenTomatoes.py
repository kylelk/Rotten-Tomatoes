#    The MIT License (MIT)
#
#    Copyright (c) 2014 kyle kersey
#
#    Permission is hereby granted, free of charge, to any person obtaining a copy
#    of this software and associated documentation files (the "Software"), to deal
#    in the Software without restriction, including without limitation the rights
#    to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#    copies of the Software, and to permit persons to whom the Software is
#    furnished to do so, subject to the following conditions:
#
#    The above copyright notice and this permission notice shall be included in all
#    copies or substantial portions of the Software.
#
#    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE


import urllib2
import json
import sqlite3
import time

# sqlite database file
cache_database = "movies.db"
# how many seconds before the entry expires
cache_expiration = 60 * 60  # one hour


class Cache:
    def get_conn(self):
        """
            connect with the sqlite database
        """
        conn = sqlite3.connect(cache_database)
        c = conn.cursor()
        c.execute(""" CREATE TABLE IF NOT EXISTS movies(
            search_query TEXT PRIMARY KEY,
            page_number INT,
            timestamp INTEGER,
            search_results BLOB); """)
        return conn

    def get(self, search_query, page_number):
        """
            get the search results from the database
        """
        with self.get_conn() as conn:
            c = conn.cursor()
            query = """SELECT search_results FROM movies WHERE
                search_query = ? AND
                page_number = ? AND
                (strftime('%s', 'now') - timestamp) < ?"""

            return c.execute(query, (search_query, page_number, cache_expiration)).fetchone()


    def put(self, search_query, page_number, search_results):
        """
            put the results into the database
        """
        timestamp = int(time.time())
        with self.get_conn() as conn:
            c = conn.cursor()
            insert = """INSERT OR REPLACE INTO movies
                        (search_query, page_number, timestamp, search_results)
                        VALUES (?, ?, ?, ?); """

            c.execute(insert, (search_query, page_number, timestamp, search_results,))
            conn.commit()


class RottenTomatoes:
    api_key = ""
    userAgent = "MovieInfoBot/1.0"

    def search(self, query, results_per_page=25, page_number=1):
        """
            searches for movies: movie name, result limit, page number
        """
        cache = Cache()
        result = cache.get(query, page_number)
        if result:
            # print "using cache"
            movie_json = result[0]
        else:
            # print "using web"
            #format the url
            base_url = "http://api.rottentomatoes.com/api/public/v1.0/movies.json"
            url = "{base_url}?apikey={api_key}&q={search_term}&page_limit={results_per_page}&page={page_number}"
            param = {}
            param["base_url"] = base_url
            param["api_key"] = self.api_key
            param["search_term"] = urllib2.quote(query.encode("utf8"))
            param["results_per_page"] = results_per_page
            param["page_number"] = page_number
            url = url.format(**param)
            req = urllib2.Request(url, headers={'User-Agent': self.userAgent})
            movie_json = urllib2.urlopen(req).read()

            # put the results into the movie cache
            cache.put(query, page_number, movie_json)

        movie_dict = json.loads(movie_json)
        return movie_dict



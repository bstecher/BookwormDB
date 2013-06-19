#!/usr/bin/python

general_prefs = dict()

general_prefs["default"] = {"fastcat": "fastcat", "HOST": "localhost", "separateDataTables": [], "fastword": "wordsheap", "database": "ThisShallBeChangedByTheInputParameter", "read_url_head": "ThisDoesn'tMatterAnyway", "fullcat": "catalog", "fullword": "words", "read_default_file": "/etc/mysql/my.cnf"}

general_prefs["movies"] = {"fastcat": "fastcat", "HOST": "localhost", "separateDataTables": [], "fastword": "wordsheap", "database": "movies", "read_url_head": "ThisDoesn'tMatterAnyway", "fullcat": "catalog", "fullword": "words", "read_default_file": "/etc/mysql/my.cnf"}

general_prefs["presidio"] = {"HOST":"melville.seas.harvard.edu","database":"presidio","fastcat":"fastcat","fullcat":"open_editions","fastword":"wordsheap","read_default_file":"/etc/mysql/my.cnf","fullword":"words","separateDataTables":["LCSH","gender"],"read_url_head":"http://www.archive.org/stream/"}
general_prefs["arxiv"] = {"HOST":"chaucer.fas.harvard.edu","database":"arxiv","fastcat":"fastcat","fullcat":"catalog","fastword":"wordsheap","fullword":"words","read_default_file":"/etc/mysql/my.cnf","separateDataTables":["genre","fastgenre","archive","subclass"],"read_url_head":"http://www.arxiv.org/abs/"}
general_prefs["jstor"] = {"HOST":"10.102.15.45","database":"jstor","fastcat":"fastcat","fullcat":"catalog","fastword":"wordsheap","fullword":"words","read_default_file":"/etc/mysql/my.cnf","separateDataTables":["discipline"],"read_url_head":"http://www.arxiv.org/abs/"}
general_prefs["HistDiss"] = {"fastcat": "fastcat", "HOST": "bookworm.culturomics.org", "separateDataTables": ["keywords"], "fastword": "wordsheap", "database": "HistDiss", "read_url_head": "arxiv.culturomics.org", "fullcat": "catalog", "fullword": "words", "read_default_file": "/etc/mysql/my.cnf"}
general_prefs["HistoryDissTest"] = {"fastcat": "fastcat", "HOST": "melville.seas.harvard.edu", "separateDataTables": ["keywords"], "fastword": "wordsheap", "database": "HistoryDissTest", "read_url_head": "arxiv.culturomics.org", "fullcat": "catalog", "fullword": "words", "read_default_file": "/etc/mysql/my.cnf"}

general_prefs["politweets"] = {"HOST":"chaucer.fas.harvard.edu","database":"politweets","fastcat":"fastcat","fullcat":"catalog","fastword":"wordsheap","fullword":"words","read_default_file":"/etc/mysql/my.cnf","separateDataTables":[],"read_url_head":"http://www.arxiv.org/abs/"}
general_prefs["LOC"] = {"HOST":"10.102.15.45","database":"LOC","fastcat":"fastcat","fullcat":"catalog","fastword":"wordsheap","fullword":"words","read_default_file":"/etc/mysql/my.cnf","separateDataTables":[],"read_url_head":"http://www.arxiv.org/abs/"}
general_prefs["ChronAm"] = {"HOST":"10.102.15.45","database":"ChronAm","fastcat":"fastcat","fullcat":"catalog","fastword":"wordsheap","fullword":"words","read_default_file":"/etc/mysql/my.cnf","separateDataTables":["subjects"],"read_url_head":"http://www.arxiv.org/abs/"}
general_prefs["ngrams"] = {"fastcat": "fastcat", "HOST": "10.102.15.45", "separateDataTables": [], "fastword": "wordsheap", "database": "ngrams", "read_url_head": "arxiv.culturomics.org", "fullcat": "catalog", "fullword": "words", "read_default_file": "/etc/mysql/my.cnf"}
general_prefs['NYT'] = {"fastcat": "fastcat", "HOST": "chaucer.fas.harvard.edu", "separateDataTables": [], "fastword": "wordsheap", "database": "NYT", "read_url_head": "nytimes.com", "fullcat": "catalog", "fullword": "words", "read_default_file": "/etc/mysql/my.cnf"}
general_prefs['NYT2'] = {"fastcat": "fastcat", "HOST": "chaucer.fas.harvard.edu", "separateDataTables": [], "fastword": "wordsheap", "database": "NYT2", "read_url_head": "nytimes.com", "fullcat": "catalog", "fullword": "words", "read_default_file": "/etc/mysql/my.cnf"}
general_prefs['NYT4'] = {"fastcat": "fastcat", "HOST": "chaucer.fas.harvard.edu", "separateDataTables": ["person", "descriptor", "title"], "fastword": "wordsheap", "database": "NYT4", "read_url_head": "arxiv.culturomics.org", "fullcat": "catalog", "fullword": "words", "read_default_file": "/etc/mysql/my.cnf"}
general_prefs['NYT5'] = {"fastcat": "fastcat", "HOST": "chaucer.fas.harvard.edu", "separateDataTables": ["person", "descriptor", "title"], "fastword": "wordsheap", "database": "NYT5", "read_url_head": "arxiv.culturomics.org", "fullcat": "catalog", "fullword": "words", "read_default_file": "/etc/mysql/my.cnf"}

#!/usr/bin/python
# -*- coding: utf-8 -*-

import MySQLdb
import re
import json
import os
from variableSet import variableSet
from variableSet import splitMySQLcode
from bookwormDB.configuration import Configfile
import logging
import warnings
import anydbm



if logging.getLogger().isEnabledFor(logging.DEBUG):
    # Catch MYSQL warnings as errors if logging is set to debug.
    warnings.filterwarnings('error', category=MySQLdb.Warning) # For testing

warnings.filterwarnings('ignore', 'Table .* already exists')
warnings.filterwarnings("ignore", "Can't create database.*; database exists")
warnings.filterwarnings("ignore", "^Unknown table .*")
warnings.filterwarnings("ignore","Table 'mysql.table_stats' doesn't exist")
warnings.filterwarnings("ignore","Data truncated for column .*")
warnings.filterwarnings("ignore","Incorrect integer value.*")


def text_id_dbm():
    """
    This quickly creates a key-value store for textids: storing on disk
    dramatically reduces memory consumption for bookworms of over 
    1 million documents.
    """
    dbm = anydbm.open(".bookworm/texts/textids.dbm","c")
    for file in os.listdir(".bookworm/texts/textids"):
        for line in open(".bookworm/texts/textids/" + file):
            line = line.rstrip("\n")
            splat = line.split("\t")
            try:
                dbm[splat[1]] = splat[0]
            except IndexError:
                if line=="":
                    # It's OK to have a blank line, let's say.
                    continue
                else:
                    raise

class DB:
    def __init__(self,dbname=None):
        try:
            configuration = Configfile("local")
            logging.debug("Connecting from the local config file")
        except IOError:
            try:
                configuration = Configfile("global")
                logging.debug("No bookworm.cnf in local file: connecting from global defaults")
            except IOError:
                configuration = Configfile("admin")
                logging.debug("No bookworm.cnf in local file: connecting from admin defaults")
                
        configuration.read_config_files()
        config = configuration.config
        if dbname==None:
            self.dbname = config.get("client","database")
        else:
            self.dbname = dbname
        self.username=config.get("client","user")
        self.password=config.get("client","password")
        self.conn = None
        
    def connect(self, setengine=True):
        #These scripts run as the Bookworm _Administrator_ on this machine; defined by the location of this my.cnf file.
        conf = Configfile("admin")
        conf.read_config_files()
        connect_args = {
            "user": conf.config.get("client","user"),
            "passwd": conf.config.get("client","password"),
            "use_unicode": 'True',
            "charset": 'utf8',
            "db": '',
            "local_infile": 1}
        try:
            self.conn = MySQLdb.connect(**connect_args)
        except MySQLdb.OperationalError:
            # Sometimes mysql wants to connect over this rather than a socket:
            # falling back to it for backward-compatibility.
            connect_args["host"] = "127.0.0.1"
            self.conn = MySQLdb.connect(**connect_args)
            
            
        cursor = self.conn.cursor()
        cursor.execute("CREATE DATABASE IF NOT EXISTS %s default character set utf8" % self.dbname)
        # Don't use native query attribute here to avoid infinite loops
        cursor.execute("SET NAMES 'utf8'")
        cursor.execute("SET CHARACTER SET 'utf8'")
        if setengine:
            try:
                cursor.execute("SET default_storage_engine=MYISAM")
            except:
                logging.error("Forcing default engine failed. On some versions of Mysql,\
                you may need to add \"default-storage-engine=MYISAM\" manually\
                to the [mysqld] user in /etc/my.cnf. Trying again to connect...")
                self.connect(setengine=False)
        logging.debug("Connecting to %s" % self.dbname)
        cursor.execute("USE %s" % self.dbname)

    def query(self, sql, silent=False, many_params=None):
        """
        Billy defined a separate query method here so that the common case of a connection being
        timed out doesn't cause the whole shebang to fall apart: instead, it just reboots
        the connection and starts up nicely again.

        silent: whether to suppress errors. Useful when an "IF EXISTS" clause doesn't work. 

        many_params: If included, assume that executemany() is expected, with the sequence of parameter
                        provided.
        """
        logging.debug(" -- Preparing to execute SQL code -- " + sql)
        try:
            cursor = self.conn.cursor()
            if many_params is not None:
                cursor.executemany(sql, many_params)
            else:
                cursor.execute(sql)
        except:
            try:
                self.connect()
                cursor = self.conn.cursor()
                if many_params is not None:
                    cursor.executemany(sql, many_params)
                else:
                    cursor.execute(sql)
            except:
                if not silent:
                    logging.error("Query failed: \n" + sql + "\n")
                    raise
        return cursor

class BookwormSQLDatabase:

    """
    This class gives interactions methods to a MySQL database storing Bookworm
    data. Although the primary methods are about loading data already created
    into the SQL database, it has a few other operations
    that write out text files needed by the API and the web front end:
    I take it as logical to do those here, since that how
    it fits chronologically in the bookworm-creation sequence.
    """

    def __init__(self,dbname=None,
                 variableFile=".bookworm/metadata/jsoncatalog_derived.txt"):
        """
        You can initialize it with a database name;
        otherwise it defaults to finding a
        Bookworm configuration file.

        It also may be initialized with a set of metadata.
        This is a little wonky, and may
        be deprecated in favor of a cleaner interface.
        """
        try:
            self.config_manager = Configfile("local")
            logging.debug("Connecting from the local config file")
        except IOError:
            try:
                self.config_manager = Configfile("global")
                logging.debug("No bookworm.cnf in local file: connecting from global defaults")
            except IOError:
                self.config_manager = Configfile("admin")
                logging.debug("No bookworm.cnf in local file: connecting from admin defaults")
                
        self.config_manager.read_config_files()
        config = self.config_manager.config
        if dbname==None:
            self.dbname = config.get("client","database")
        else:
            self.dbname = dbname
        self.conn = None

        self.db = DB(dbname=self.dbname)
        
        if variableFile is not None:
            self.setVariables(originFile=variableFile)

    def grantPrivileges(self):
        """
        Grants select-only privileges to a non-admin mysql user for the API to
        query with (safer).

        The Username for these privileges is pulled from the bookworm.cnf file.
        """

        globalfile = Configfile("global")
        globalfile.read_config_files()

        username=globalfile.config.get("client","user")
        password=globalfile.config.get("client","password")

        self.db.query("GRANT SELECT ON %s.* TO '%s'@'localhost' IDENTIFIED BY '%s'" % (self.dbname,username,password))
    
    def setVariables(self,originFile,anchorField="bookid",
                     jsonDefinition=".bookworm/metadata/field_descriptions_derived.json"):
        self.variableSet = variableSet(originFile=originFile, anchorField=anchorField, jsonDefinition=jsonDefinition,db=self.db)

    def importNewFile(self,originFile,anchorField,jsonDefinition):
        """
        Add additional metadata from a source collection of json-formatted rows.
        originFile is the filename of the new metadata, in the same input format
        as the original jsoncatalog.txt
        anchorField is the field in the existing dataset it should be anchored onto;
        jsonDefinition is a filename pointing to a file
        of the format of field_descriptions.json describing the new data to ingest.
        If it is of type None, then one will be guessed at.
        """
        self.setVariables(originFile,anchorField=anchorField,jsonDefinition=jsonDefinition)
        self.variableSet.writeMetadata()
        self.load_book_list()
        self.variableSet.updateMasterVariableTable()
        for variable in self.variableSet.variables:
            variable.clear_associated_memory_tables()
        self.reloadMemoryTables()

    def create_database(self):
        dbname = self.dbname
        dbuser = self.dbuser
        dbpassword = self.dbpassword
        db = self.db
        #This must be run as a MySQL user with create_table privileges
        try:
            db.query("CREATE DATABASE " + dbname)
        except:
            logging.info("Database %s already exists: that might be intentional, so not dying" % dbname)

        "Setting up permissions for web user..."
        db.query("GRANT SELECT ON " + dbname + ".*" + " TO '" + dbuser + "'@'localhost' IDENTIFIED BY '" + dbpassword + "'")
        db.query("FLUSH PRIVILEGES")
        try:
            #a field to store stuff we might need later.
            db.query("CREATE TABLE IF NOT EXISTS bookworm_information (entry VARCHAR(255), PRIMARY KEY (entry), value VARCHAR(50000))")
        except:
            raise

    def load_word_list(self):
        db = self.db
        logging.info("Making a SQL table to hold the words")
        db.query("""DROP TABLE IF EXISTS words""")
        db.query("""CREATE TABLE IF NOT EXISTS words (
        wordid MEDIUMINT UNSIGNED NOT NULL,
        word VARCHAR(255), INDEX (word),
        count BIGINT UNSIGNED,
        casesens VARBINARY(255),
        stem VARCHAR(255)
        );""")

        db.query("ALTER TABLE words DISABLE KEYS")
        logging.info("loading data using LOAD DATA LOCAL INFILE")
        db.query("""LOAD DATA LOCAL INFILE '.bookworm/texts/wordlist/wordlist.txt'
                   INTO TABLE words
                   CHARACTER SET binary
                   (wordid,word,count) """)
        logging.info("creating indexes on words table")
        db.query("ALTER TABLE words ENABLE KEYS")
        db.query("UPDATE words SET casesens=word")

    def load_book_list(self):
        """
        Loads in the tables that have already been created by a previous
        call to `Bookworm.variableSet.writeMetadata()`
        """
        self.variableSet.loadMetadata()

    def create_unigram_book_counts(self, newtable=True, ingest=True, index=True, reverse_index=True, table_count=1):
        import time
        t0 = time.time()

        db = self.db
        ngramname = "unigrams"
        tablenameroot = "master_bookcounts"
        # If you are splitting the input into multiple tables
        # to be joined as a merge table, come up with multiple 
        # table names and we'll cycle through.
        if table_count == 1:
            tablenames = [tablenameroot]
        elif table_count > 1:
            tablenames = ["%s_p%d" % (tablenameroot, i) for i in range(1, table_count+1)]
        else:
            logging.error("You need a positive integer for table_count")
            raise

        grampath =  ".bookworm/texts/encoded/%s" % ngramname
        tmpdir = "%s/tmp" % grampath

        if (len(grampath) == 0) or (grampath == "/"):
            logging.error("Woah! Don't set the ngram path to your system root!")
            raise
        
        if newtable:
            if os.path.exists(tmpdir):
                import shutil
                shutil.rmtree(tmpdir)
        
            logging.info("Dropping older %s table, if it exists" % ngramname)
            for tablename in tablenames:
                db.query("DROP TABLE IF EXISTS " + tablename)

        logging.info("Making a SQL table to hold the %s" % ngramname)
        reverse_index_sql = "INDEX(bookid,wordid,count), " if reverse_index else ""
        for tablename in tablenames:
            db.query("CREATE TABLE IF NOT EXISTS " + tablename + " ("
                "bookid MEDIUMINT UNSIGNED NOT NULL, " + reverse_index_sql +
                "wordid MEDIUMINT UNSIGNED NOT NULL, INDEX(wordid,bookid,count), "
                "count MEDIUMINT UNSIGNED NOT NULL);")

        if ingest:
            for tablename in tablename:
                db.query("ALTER TABLE " + tablename + " DISABLE KEYS")
            db.query("set NAMES utf8;")
            db.query("set CHARACTER SET utf8;")
            logging.info("loading data using LOAD DATA LOCAL INFILE")
            
            files = os.listdir(grampath)
            for i, filename in enumerate(files):
                if filename.endswith('.txt'):
                    # With each input file, cycle through each table in tablenames
                    tablename = tablenames[i % len(table_names)]
                    logging.debug("Importing txt file, %s (%d/%d)" % (filename, i, len(files)))
                    try:
                        db.query("LOAD DATA LOCAL INFILE '" + grampath + "/" + filename + "' INTO TABLE " + tablename +" CHARACTER SET utf8 (bookid,wordid,count);")
                    except KeyboardInterrupt:
                        raise
                    except:
                       logging.debug("Falling back on insert without LOCAL DATA INFILE. Slower.")
                       try:
                            import pandas as pd
                            df = pd.read_csv(grampath + "/" + filename, sep='\t', header=None)
                            to_insert = df.apply(tuple, axis=1).tolist()
                            db.query(
                                "INSERT INTO " + tablename + " (bookid,wordid,count) "
                                "VALUES (%s, %s, %s);""",
                                many_params=to_insert
                                )
                       except KeyboardInterrupt:
                           raise
                       except:
                           logging.exception("Error inserting %s from %s" % (ngramname, filename))
                           continue

                elif filename.endswith('.h5'):
                    logging.info("Importing h5 file, %s (%d/%d)" % (filename, i, len(files)))
                    try:
                        # When encountering an .h5 file, this looks for ngram information
                        # in a /#{ngramnames} table (e.g. /unigrams) and writes it out to
                        # temporary TSV files.
                        # Dask is used here simply because it's a dead simple way to multithread
                        # the TSV writing and lower the overhead versus having a TSV already staged.
                        import csv
                        import pandas as pd
                        try:
                            import dask.dataframe as dd
                        except:
                            logging.exception("Ingesting h5 files requires dask")
                        try:
                            os.makedirs(tmpdir)
                        except OSError:
                            if not os.path.isdir(tmpdir):
                                raise
                        # Dask will use #{n_cores-1} threads when saving CSVs.
                        # Ingest and key reload times are identical to txt import, so the only
                        # additional overhead is reading the file (small effect) and writing the csv.
                        ddf = dd.read_hdf(grampath + "/" + filename,
                                          ngramname, mode='r', chunksize=2000000)
                        ddf.reset_index().to_csv(tmpdir + '/tmp.*.tsv',
                                                 index=False, sep='\t', header=False,
                                                 quoting=csv.QUOTE_NONNUMERIC)
                        logging.info("CSV written from H5. Time passed: %.2f s" % (time.time() - t0))
                        for j, tmpfile in enumerate(os.listdir(tmpdir)):
                            # With each input file, cycle through each table in tablenames
                            tablename = tablenames[j % len(table_names)]
                            path = "%s/%s" % (tmpdir, tmpfile)
                            db.query("LOAD DATA LOCAL INFILE '" + path + "' "
                                     "INTO TABLE " + tablename + " "
                                     "CHARACTER SET utf8 (bookid,wordid,count);")
                            try:
                                os.remove(path)
                            except:
                                pass
                        logging.info("CSVs input. Time passed: %.2f s" % (time.time() - t0))
                    except KeyboardInterrupt:
                       raise
                    except:
                       logging.exception("Error inserting %s from %s" % (ngramname, filename))
                       continue
                else:
                    continue
        if index:
            logging.info("Creating Unigram Indexes. Time passed: %.2f s" % (time.time() - t0))
            for tablename in tablenames:
                db.query("ALTER TABLE " + tablename + " ENABLE KEYS")

        logging.info("Unigram index created in: %.2f s" % ((time.time() - t0)))

    def create_bigram_book_counts(self):
        db = self.db
        logging.info("Making a SQL table to hold the bigram counts")
        db.query("""DROP TABLE IF EXISTS master_bigrams""")
        db.query("""CREATE TABLE master_bigrams (
        bookid MEDIUMINT UNSIGNED NOT NULL,
        word1 MEDIUMINT UNSIGNED NOT NULL, INDEX (word1,word2,bookid,count),
        word2 MEDIUMINT UNSIGNED NOT NULL,
        count MEDIUMINT UNSIGNED NOT NULL);""")
        db.query("ALTER TABLE master_bigrams DISABLE KEYS")
        logging.info("loading data using LOAD DATA LOCAL INFILE")
        for filename in os.listdir(".bookworm/texts/encoded/bigrams"):
            try:
                db.query("LOAD DATA LOCAL INFILE '.bookworm/texts/encoded/bigrams/"+filename+"' INTO TABLE master_bigrams CHARACTER SET utf8 (bookid,word1,word2,count);")
            except:
                raise
        logging.info("Creating bigram indexes")
        db.query("ALTER TABLE master_bigrams ENABLE KEYS")

    def loadVariableDescriptionsIntoDatabase(self):
        """
        This adds a description of files to the master variable table:
        also, crucially, it puts code specifying their fast creation there,
        where it will be executed on startup for all eternity.
        """
        logging.debug("Building masterVariableTable")
        db = self.db
        db.query("DROP TABLE IF EXISTS masterVariableTable")
        m = db.query("""
            CREATE TABLE IF NOT EXISTS masterVariableTable
              (dbname VARCHAR(255), PRIMARY KEY (dbname),
              name VARCHAR(255),
              type VARCHAR(255),
              tablename VARCHAR(255),
              anchor VARCHAR(255),
              alias VARCHAR(255),
              status VARCHAR(255),
              description VARCHAR(5000)
              ) ENGINE=MYISAM;
              """)
        tableTable = db.query("""
            CREATE TABLE IF NOT EXISTS masterTableTable
              (tablename VARCHAR(255), PRIMARY KEY (tablename),
              dependsOn VARCHAR(255),
              memoryCode VARCHAR(20000)) ENGINE=MYISAM;
              """)
        self.addFilesToMasterVariableTable()
        self.addWordsToMasterVariableTable()
        self.variableSet.updateMasterVariableTable()

    def reloadMemoryTables(self,force=False):
        """
        Checks to see if memory tables need to be repopulated (by seeing if they are empty)
        and then does so if necessary.
        """
        existingCreateCodes = self.db.query("SELECT tablename,memoryCode FROM masterTableTable").fetchall()
        for row in existingCreateCodes:
            """
            For each table, it checks to see if the table is currently populated; if not,
            it runs the stored code to repopulate the table. (It checks length because
            memory tables are emptied on a restart).
            """
            tablename = row[0]
            try:
                cursor = self.db.query("SELECT count(*) FROM %s" %(tablename), silent = True)
                currentLength = cursor.fetchall()[0][0]
                logging.debug("Current Length is %d" %currentLength)
            except:
                currentLength = 0
            if currentLength==0 or force:
                for query in splitMySQLcode(row[1]):
                    self.db.query("SET optimizer_search_depth=0")
                    self.db.query(query)

    def addFilesToMasterVariableTable(self):
        fastFieldsCreateList = ["bookid MEDIUMINT UNSIGNED NOT NULL, PRIMARY KEY (bookid)","nwords MEDIUMINT UNSIGNED NOT NULL"] +\
          [variable.fastSQL() for variable in self.variableSet.variables if (variable.unique and variable.fastSQL() is not None)]
        fileCommand = """DROP TABLE IF EXISTS tmp;
        CREATE TABLE tmp
        (""" +",\n".join(fastFieldsCreateList) + """
        ) ENGINE=MEMORY;"""
        #Also update the wordcounts for each text.
        fastFields = ["bookid","nwords"] + [variable.fastField for variable in self.variableSet.variables if variable.unique and variable.fastSQL() is not None]
        fileCommand += "INSERT INTO tmp SELECT " + ",".join(fastFields) + " FROM catalog USE INDEX () " + " ".join([" JOIN %(field)s__id USING (%(field)s ) " % variable.__dict__ for variable in self.variableSet.variables if variable.unique and variable.fastSQL() is not None and variable.datatype=="categorical"])+ ";"
        fileCommand += "DROP TABLE IF EXISTS fastcat;"
        fileCommand += "RENAME TABLE tmp TO fastcat;"
        self.db.query('DELETE FROM masterTableTable WHERE masterTableTable.tablename="fastcat";')
        self.db.query("""INSERT IGNORE INTO masterTableTable VALUES
                   ('fastcat','fastcat','""" + fileCommand + """')""")

    def addWordsToMasterVariableTable(self):
        wordCommand = "DROP TABLE IF EXISTS tmp;"
        wordCommand += "CREATE TABLE tmp (wordid MEDIUMINT UNSIGNED NOT NULL, PRIMARY KEY (wordid), word VARCHAR(30), INDEX (word), casesens VARBINARY(30),UNIQUE INDEX(casesens), lowercase CHAR(30), INDEX (lowercase) ) ENGINE=MEMORY;"
        wordCommand += "INSERT IGNORE INTO tmp SELECT wordid as wordid,word,casesens,LOWER(word) FROM words WHERE CHAR_LENGTH(word) <= 30 AND wordid <= 1500000 ORDER BY wordid;"
        wordCommand += "DROP TABLE IF EXISTS wordsheap;"
        wordCommand += "RENAME TABLE tmp TO wordsheap;"
        query = """INSERT IGNORE INTO masterTableTable
                   VALUES ('wordsheap','wordsheap','""" + MySQLdb.escape_string(wordCommand) + """')"""
        logging.info("Creating wordsheap")
        self.db.query(query)
        
    def jsonify_data(self):
        variables = self.variableSet.variables
        dbname = self.dbname
        #This creates a JSON file compliant with the Bookworm web site.
        #Deprecated.
        output = dict()
        output['settings'] = {
                              "dbname": self.dbname,
                              "itemName":" text",
                              "sourceName": self.dbname,
                              "sourceURL": self.dbname
                             }
        ui_components = [
                         {
                          "type":"text",
                          "dbfield":"word",
                          "name":"Word(s)"
                         }
                        ]
        for variable in variables:
            newdict = variable.jsonDict()
            if newdict: #(It can be empty, in which case we don't want it for the json)
                ui_components.append(newdict)
        try:
            mytime = [variable.field for variable in variables if variable.datatype=='time'][0]
            output['default_search'] = [
                                         {
                                          "search_limits": [{"word":["test"]}],
                                          "time_measure": mytime,
                                          "words_collation": "Case_Sensitive",
                                          "counttype": "Occurrences_per_Million_Words",
                                          "smoothingSpan": 0
                                         }
                                        ]
        except:
            logging.warning("WARNING: Not enough info for a default search (like, no time variable maybe?)--likely to be some big problems with your bookworm.")
        output['ui_components'] = ui_components
        outfile = open('.bookworm/%s.json' % dbname, 'w')
        outfile.write(json.dumps(output))

    def create_API_settings(self):
        db = self.db
        try:
            db.query("DROP TABLE IF EXISTS API_settings")
            db.query("CREATE TABLE API_settings (settings VARCHAR(8192));")
        except:
            pass
        api_info = {
                    "HOST": "10.102.15.45",
                    "database": self.dbname,
                    "read_default_file": "/etc/mysql/my.cnf",
                   }
        addCode = json.dumps(api_info)
        logging.info(addCode)
        db.query("INSERT INTO API_settings VALUES ('%s');" % addCode)

    def update_Porter_stemming(self): #We use stems occasionally.
        """
        Still not executed.
        """
        logging.info("Updating stems from Porter algorithm...")
        from nltk import PorterStemmer
        db = self.db

        stemmer = PorterStemmer()
        cursor = db.query("""SELECT word FROM words""")
        words = cursor.fetchall()
        for local in words:
            word = ''.join(local)  # Could probably take the first element of the tuple as well?
            # Apostrophes have the save stem as the word, if they're included
            word = word.replace("'s","")
            if re.match("^[A-Za-z]+$",word):
                query = """UPDATE words SET stem='""" + stemmer.stem(''.join(local)) + """' WHERE word='""" + ''.join(local) + """';"""
                z = cursor.execute(query)


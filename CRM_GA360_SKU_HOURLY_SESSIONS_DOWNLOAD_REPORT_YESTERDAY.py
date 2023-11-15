from __future__ import print_function

__author__ = 'gowtham.patnaik@publicissapient.com'

import argparse
import sys
import datetime
from datetime import timedelta, date
import array
import os
from googleapiclient.errors import HttpError
from googleapiclient import sample_tools
from oauth2client.client import AccessTokenRefreshError
from pprint import pprint
import pandas as pd
import configparser
import ssl
import socket
socket.setdefaulttimeout(600)
from google.cloud import storage

 
configParser = configparser.RawConfigParser()
configFilePath = 'config_all.ini'
configParser.read(configFilePath)

os.environ[
    "GOOGLE_APPLICATION_CREDENTIALS"] = configParser.get(section='global', option='PATH_TO_SERVICE_KEY_FILE')
   

# Declare all-parameters flags.
table_id = configParser.get('CRM_GA360_SKU_HOURLY_SESSIONS_REPORT','table_id')
#val_start_date =  configParser.get('CRM_GA360_SKU_HOURLY_SESSIONS_REPORT','val_start_date')
val_start_date=datetime.datetime.now()- datetime.timedelta(days=1) 
#val_end_date = configParser.get('CRM_GA360_SKU_HOURLY_SESSIONS_REPORT','val_start_date')
val_end_date=datetime.datetime.now() - datetime.timedelta(days=1) 
val_metrics = configParser.get('CRM_GA360_SKU_HOURLY_SESSIONS_REPORT','val_metrics')
val_dimensions = configParser.get('CRM_GA360_SKU_HOURLY_SESSIONS_REPORT','val_dimensions')
val_sort = configParser.get('CRM_GA360_SKU_HOURLY_SESSIONS_REPORT','val_sort')
val_filters = configParser.get('CRM_GA360_SKU_HOURLY_SESSIONS_REPORT','val_filters')
val_start_index = configParser.get('CRM_GA360_SKU_HOURLY_SESSIONS_REPORT','val_start_index')
val_max_results = configParser.get('CRM_GA360_SKU_HOURLY_SESSIONS_REPORT','val_max_results')
DATE = datetime.datetime.now().strftime("%Y%m%d") 
DATETIME = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
yesterday = datetime.datetime.now() - datetime.timedelta(days=1)
formatted_date = yesterday.strftime("%Y%m%d")
current_datetime = datetime.datetime.now()
one_day_ago = current_datetime - datetime.timedelta(days=1)
formatted_datetime = one_day_ago.replace(hour=23, minute=59, second=0).strftime("%Y%m%d%H%M%S")

def main(argv):
    # Authenticate and construct service.
    service, flags = sample_tools.init(
        argv, 'analytics', 'v3', __doc__, __file__, parents=[],
        scope='https://www.googleapis.com/auth/analytics.readonly')

    # Try to make a request to the API. Print the results or handle errors.
    try:

        # function to get the date range from startdate to end date
        def daterange(val_start_date, val_end_date):
         for n in range(int((val_end_date - val_start_date).days)+int(1)):
            yield val_start_date + timedelta(n) 

        # call API to get the results
        date= val_start_date.strftime("%Y-%m-%d")
        results = get_api_query(service, val_start_index = '1',date=date).execute()

        # Fetch the headers
        df_header = []
        i = 0
        for i in results['columnHeaders']:
            df_header.append(i['name'])
        print("Header : " , df_header)
        header = pd.Series(df_header)
        header_df = pd.DataFrame([header])
        df_result = pd.DataFrame()
        total_rows = 0

        # Loop through the date range and fetch the day wise results from API in the data range defined
        for single_date in daterange(val_start_date,val_end_date) :
            date= single_date.strftime("%Y-%m-%d")
            
            print("-----------------------Date - {}-----------------------------".format(date))

            # fetch the result set from API for each date
            result1 = get_api_query(service, val_start_index = '1',date=date).execute() 
            new_df = pd.DataFrame(result1['rows'], columns = df_header)

            print(new_df)     
            added_rows = result1['itemsPerPage']
       
        
            # Count total number of rows
            total_rows =  total_rows + result1['totalResults']
            print('total rows {}'.format(result1['totalResults']))
            val_start_index = 1
            
            # Check if data is present in the next page, If yes, Fetch the data in the next pages else exit from the loop
            while(result1['totalResults'] > added_rows):
                val_start_index = val_start_index + result1['itemsPerPage']  
                added_rows =  added_rows + result1['itemsPerPage']                 
                
                results2 = get_api_query(service, val_start_index,date).execute()
                print('start_index {}'.format(val_start_index))
                print('more rows to fetch')
                
                new_df1 = pd.DataFrame(results2['rows'], columns = df_header)
                print(new_df1)

                df_result = pd.concat([df_result, new_df1], ignore_index=True, sort=False)   

            # appends the data for all the dates    
            df_result = pd.concat([df_result, new_df], ignore_index=True, sort=False)    

        print("-----------------------------Summary-----------------------------------------")
        print('total rows from : ',val_start_date.strftime("%Y-%m-%d"),' to ',val_end_date.strftime("%Y-%m-%d"),' is : {}'.format(total_rows))

        # Copy the data into the local storage
        if not os.path.exists(configParser.get('GA360','LOCAL_FOLDER_PATH_TO_REPORT')+configParser.get('GA360','CRM_FILE_PREFIX_SKU_HOURLY_SESSIONS')+  format(formatted_date)+  '/' +format(formatted_datetime)):
            os.makedirs(configParser.get('GA360','LOCAL_FOLDER_PATH_TO_REPORT')+configParser.get('GA360','CRM_FILE_PREFIX_SKU_HOURLY_SESSIONS')+  format(formatted_date)+  '/' +format(formatted_datetime))    
        df_result.to_csv(configParser.get('GA360','LOCAL_FOLDER_PATH_TO_REPORT')+ configParser.get('GA360','CRM_FILE_PREFIX_SKU_HOURLY_SESSIONS')+  format(formatted_date) +  '/' +format(formatted_datetime)+ '/' + configParser.get('GA360','CRM_FILE_PREFIX_SKU_HOURLY_SESSIONS')+  format(formatted_datetime)+'.csv', index = None, header=True)
        #print(df_result)

    except TypeError as error:
        # Handle errors in constructing a query.
        print(('There was an error in constructing your query : %s' % error))

    except HttpError as error:
        # Handle API errors.
        print(('Arg, there was an API error : %s : %s' %
               (error.resp.status, error._get_reason())))

    except AccessTokenRefreshError:
        # Handle Auth errors.
        print('The credentials have been revoked or expired, please re-run '
              'the application to re-authorize')

    except ssl.SSLError as err:
        # Handle SSL errors.
        print('Scoket timeout')

def get_api_query(service, val_start_index,date):
    """Returns a query object to retrieve data from the Core Reporting API.

  Args:
    service: The service object built by the Google API Python client library.
    table_id: str The table ID form which to retrieve data.
  """

    return service.data().ga().get(
        ids=table_id,
        start_date=date,
        end_date=date,
        metrics=val_metrics,
        dimensions=val_dimensions,
        sort=val_sort,
        filters=val_filters,
        start_index=val_start_index,
        max_results=val_max_results,
        samplingLevel= 'HIGHER_PRECISION'
        )

# upload file to cloud storage from local folder

BUCKET_STORAGE_NAME = 'ga360_hourly_report_data'
LOCAL_FOLDER = configParser.get('GA360','LOCAL_FOLDER_PATH_TO_REPORT')+configParser.get('GA360','CRM_FILE_PREFIX_SKU_HOURLY_SESSIONS') + format(formatted_date) + '/' +format(formatted_datetime)
BUCKET_FOLDER = 'ga360_sku_hourly_sessions' + '/' + format(formatted_date)
TOTAL_CSV_ROWS = 0
global TOTAL_TABLE_ROWS_BEFORE_UPLOAD
TOTAL_TABLE_ROWS_BEFORE_UPLOAD = 0
global TOTAL_TABLE_ROWS_AFTER_UPLOAD
TOTAL_TABLE_ROWS_AFTER_UPLOAD = 0
global NUMBER_OF_ROWS_UPLOADED
NUMBER_OF_ROWS_UPLOADED = 0
print(BUCKET_FOLDER)

def upload_files_to_cloud_storage(bucketName):
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(bucketName)
    """Upload files to GCP bucket."""
    files = [f for f in os.listdir(LOCAL_FOLDER ) if os.path.isfile(os.path.join(LOCAL_FOLDER, f))]
    for file in files:
        localFile = LOCAL_FOLDER + '/' + file
        with open(localFile, 'r',encoding='latin-1') as f:
            file1 = f.readlines()
        global TOTAL_CSV_ROWS
        TOTAL_CSV_ROWS = len(file1)
        print('total csv rows', format(TOTAL_CSV_ROWS))
        blob = bucket.blob(BUCKET_FOLDER + '/' + file)
        blob.upload_from_filename(localFile)
    return 'Uploaded {} to {} bucket.'.format(files,bucketName)




if __name__ == '__main__':
    main(sys.argv)
    upload_files_to_cloud_storage(bucketName=BUCKET_STORAGE_NAME)
    print('Total number of CSV rows are {} '.format(TOTAL_CSV_ROWS))

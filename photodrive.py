# Author Joey Whelan

from googleapiclient.discovery import build
from google.oauth2 import service_account
from googleapiclient.http import MediaFileUpload 
from PIL import Image 
import os

GDRIVE_ROOT = 'Whelan Family Photos'
LOCAL_ROOT = '/nas/pictures'
CREDENTIALS = 'credentials.json'
SCOPES = ['https://www.googleapis.com/auth/drive']
NUM_TRIES = 3

class GDrive(object):
    def __init__(self):
        sa_creds = service_account.Credentials.from_service_account_file(CREDENTIALS)
        scoped_creds = sa_creds.with_scopes(SCOPES)
        self.service = build('drive', 'v3', credentials=scoped_creds)
        self.root_folder_id = self.get_folder_id(GDRIVE_ROOT)
    
    def create_folder(self, folder_name,  parent_id=None):
        file_metadata = {'name': folder_name,
            'parents' : [parent_id],
            'mimeType': 'application/vnd.google-apps.folder'
        }
        print('creating folder: ' + folder_name)
        folder = self.service.files().create(body=file_metadata,
                                    fields='id').execute(num_retries=NUM_TRIES)
        return folder['id']

    def get_file_list(self,
                    folder_id):
        page_token = None
        items = []
        while True:
            results = self.service.files().list(q="'" + folder_id + "' in parents", 
                                                spaces='drive',
                                                fields='nextPageToken, files(id, name)',
                                                pageToken=page_token).execute(num_retries=NUM_TRIES)
            for item in results.get('files', []):
                items.append(item)
            page_token = results.get('nextPageToken', None)
            if page_token is None:
                break

        return items

    def get_folder_id(self,
                    folder_name):
        query = "trashed = false and mimeType = 'application/vnd.google-apps.folder' and name='" + folder_name + "'"
        results = self.service.files().list(q=query, 
                                                spaces='drive',
                                                fields='files(id)').execute(num_retries=NUM_TRIES)
        items = results.get('files', [])

        if not items:
            return None
        else:
            return items[0]['id']

    def resize(self, 
            infile):
        outfile = os.path.join('./', os.path.basename(infile))
        im = Image.open(infile)
        if max(im.size) < 1000:
            size = im.size
        else:
            size = (1000,1000)

        im.thumbnail(size, Image.ANTIALIAS)
        im.save(outfile, optimize=True, quality=85)
        return outfile

    def upload_all_images(self):
        years = os.listdir(LOCAL_ROOT)

        for year in years:
            print('Uploading year: ' + year)
            year_path = os.path.join(LOCAL_ROOT, year)
            year_months = os.listdir(year_path)
            for year_month in year_months:
                print('Uploading year_month: ' + year_month)
                self.upload_folder_images(year, year_month)

    def upload_file(self,
                    local_file_path,
                    folder_id):

        file_name = os.path.basename(local_file_path)
        #check if file already exists on gdrive.  if not, create the file on google drive.
        results = self.service.files().list(q="'" + folder_id + "' in parents and name = '"  + file_name + "'", 
                                                spaces='drive',
                                                fields='files(id)').execute(num_retries=NUM_TRIES)
        items = results.get('files', [])
        if not items:
            print('Uploading: ' + file_name)
            try:
                outfile = self.resize(local_file_path)
                media = MediaFileUpload(outfile)
                file_metadata = {'name': file_name, 'parents': [folder_id]}
                self.service.files().create(body=file_metadata,
                                media_body=media,
                                fields='id').execute(num_retries=NUM_TRIES)
                os.remove(outfile)
            except Exception as e:
                print(e)
        else:
            print('File already exists on gdrive: ' + file_name)
        return 
    
    def upload_folder_images(self,
                    year,
                    year_month):
        year_month_path = os.path.join(os.path.join(LOCAL_ROOT, year), year_month)
        if (os.path.isdir(year_month_path)):
            year_folder_id = self.get_folder_id(year)
            if (not year_folder_id):
                year_folder_id = self.create_folder(year, self.root_folder_id)
       
            year_month_folder_id = self.get_folder_id(year_month)
            if (not year_month_folder_id):
                year_month_folder_id = self.create_folder(year_month, year_folder_id)

            for file in os.listdir(year_month_path):
                local_file_path = os.path.join(year_month_path,file)
                if (os.path.isfile(local_file_path)):
                    try:
                        self.upload_file(local_file_path, year_month_folder_id)      
                    except Exception as e:
                        print(e)
      
    def clear_drive(self):
        page_token = None

        while True:
            results = self.service.files().list(
                        pageSize=1000, 
                        spaces='drive',
                        fields="nextPageToken, files(id, name)",
                        pageToken=page_token).execute(num_retries=NUM_TRIES)
            for file in results.get('files', []):
                name = file.get('name')
                id = file.get('id')
                if name != GDRIVE_ROOT:
                    print('Deleting name: ' + name + ' id: ' + id)
                    try:
                        self.service.files().delete(fileId=id).execute()
                    except:
                        print('error')
            page_token = results.get('nextPageToken', None)
            if page_token is None:
                break

if __name__ == '__main__':
    gdrive = GDrive()
    #gdrive.clear_drive()
    gdrive.upload_all_images()

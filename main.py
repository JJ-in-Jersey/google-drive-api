import os
# import io
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
# from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

from tt_dictionary.dictionary import Dictionary
from tt_dataframe.dataframe import DataFrame
from tt_exceptions.exceptions import GoogleAuthenticationFailure, GoogleServiceBuildFailure

# Define the scopes required for Google Drive API access.
# 'https://www.googleapis.com/auth/drive' gives full access to Google Drive.
# For more restricted access, you might
# use 'https://www.googleapis.com/auth/drive.file'
# which only allows access to files created or opened by the app.
SCOPES = ['https://www.googleapis.com/auth/drive']
CLIENT_SECRET_JSON = 'client_secret.json'
TOKEN_JSON = 'token.json'
DRIVE_JSON = Path('google_drive.json')
CSV_PREFIX = 'https://drive.google.com/file/d/'
CSV_SUFFIX = '/view?usp=drive_link'
FOLDER_MIMETYPE = 'application/vnd.google-apps.folder'
PNG_MIMETYPE = 'image/png'
FILE_MIMETYPE = 'application/vnd.google-apps.file'
IMAGES_FOLDER = 'images 3.0'
GOOGLE_URLS_CSV = 'google_urls.csv'


def authenticate_google_drive():
    """
    Handles Google Drive API authentication.
    It checks for existing credentials, refreshes them if expired,
    or initiates a new OAuth 2.0 flow if no credentials are found.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists(TOKEN_JSON):
        creds = Credentials.from_authorized_user_file(TOKEN_JSON, SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # The client_secrets.json file contains your OAuth 2.0 client ID and client secret.
            # You download this from the Google Cloud Console.
            if Path(CLIENT_SECRET_JSON).exists():
                flow = InstalledAppFlow.from_client_secrets_file(
                    CLIENT_SECRET_JSON, SCOPES)
                creds = flow.run_local_server(port=0)
            else:
                raise GoogleAuthenticationFailure('No credentials file found')

        # Save the credentials for the next run
        with open(TOKEN_JSON, 'w') as token:
            token.write(creds.to_json())
    return creds


def build_drive_service(creds):
    """
    Builds and returns the Google Drive API service object.
    """
    try:
        service = build('drive', 'v3', credentials=creds)
        print("Google Drive service built successfully.")
        return service
    except HttpError as error:
        print(f"An error occurred while building the Drive service: {error}")
        return None


def delete_file(service, file_name: str, file_id: str):
    """
    Deletes a file from Google Drive.
    Args:
        service: The Google Drive API service object.
        file_name: The name of the file to delete.
        file_id: The ID of the file to delete.
    """
    print(f"\n--- Deleting File ({file_name}: {file_id}) ---")
    try:
        service.files().delete(fileId=file_id).execute()
        print(f"File ({file_name}: {file_id}) deleted successfully.")
    except HttpError as error:
        print(f"An error occurred while deleting file: {error}")


def build_dict_from_folder(service, folder_name: str = None):
    """
    Fetches files and folders from Google Drive starting from a specific non-root folder.

    Args:
        service: The authenticated Google Drive API service object.
        folder_name: The name of the folder to start fetching from.

    Returns:
        # list: A list of dictionaries, each representing a file or folder with its metadata.
        dict: a dictionary containing the file/folder tree and all the file/folder metadata
    """

    master_dict = Dictionary()
    master_dict['name_id'] = None
    master_dict['id_item'] = Dictionary()
    master_dict['id_name'] = Dictionary()
    folder_id = get_folder_id_by_name(service, folder_name)

    # Helper recursive function to fetch descendants of a given folder
    def fetch_descendants_recursive(current_folder_id, level: int = 0, max_name_length: int = 0):
        indent = 2 * level * ' '
        level += 1

        current_folder_name = master_dict['id_name'].get(current_folder_id)
        current_folder_dict = master_dict['id_item'].get(current_folder_id)
        current_folder_dict.pop('mimeType')

        if max_name_length - len(current_folder_name) > 0:
            indent += ' ' * (max_name_length - len(current_folder_name))

        print(indent + current_folder_name)

        page_token = None
        while True:
            try:
                query = f"'{current_folder_id}' in parents and trashed=false"
                response = service.files().list(q=query, spaces='drive', fields='nextPageToken, files(id, name, mimeType, size)', pageToken=page_token).execute()
                current_items = response.get('files', [])

                max_name_length = 0
                for item in current_items:
                    item = Dictionary(item)
                    name = item.pop('name')
                    if item.get('mimeType') == FOLDER_MIMETYPE and max_name_length < len(name):
                        max_name_length = len(name)
                    master_dict['id_name'][item['id']] = name
                    master_dict['id_item'][item['id']] = item
                    current_folder_dict[name] = item

                for item in current_items:
                    if item.get('mimeType') == FOLDER_MIMETYPE:
                        fetch_descendants_recursive(item['id'], level, max_name_length)  # Recursive call
                    else:
                        item.pop('mimeType')

                page_token = response.get('nextPageToken', None)
                if not page_token:
                    break
            except HttpError as error:
                print(f"An error occurred while fetching descendants of folder ID '{current_folder_id}': {error}")
                break


    # If a specific folder ID, start the recursive fetching
    # First, fetch the metadata of the start_folder_id itself, as it's the root of the desired tree
    if folder_id is not None:
        try:
            item = service.files().get(fileId=folder_id, fields='id, name, mimeType, size').execute()
            item = Dictionary(item)
            name = item.pop('name')
            master_dict['id_name'][item.get('id')] = name
            master_dict['id_item'][item.get('id')] = item
            master_dict[name] = item

            fetch_descendants_recursive(item.get('id'))
        except HttpError as error:
            print(f"Error fetching metadata for start folder ID '{folder_id}': {error}")
            return []  # Return empty if the start folder itself can't be fetched or is invalid


    master_dict['name_id'] = master_dict['id_name'].reverse()
    return master_dict


def get_folder_id_by_name(service, folder_name: str):
    """
    Find the ID of a folder by its name, specifically looking for direct children of 'My Drive'.

    Args:
        service: The authenticated Google Drive API service object.
        folder_name (str): The name of the folder to search for.
    Returns:
        str: The ID of the found folder, or None if not found.
    """
    try:
        # Query for folders with the given name and whose parent is 'root' (My Drive)
        query = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and 'root' in parents and trashed=false"
        response = service.files().list(q=query, spaces='drive', fields='files(id, name, parents)').execute()
        folders = response.get('files', [])
        if folders:
            print(f"Found top-level folder '{folder_name}' with ID: {folders[0]['id']}")
            return folders[0]['id']  # Return the ID of the first matching folder
        else:
            print(f"Folder '{folder_name}' not found at the highest level of your Drive.")
            return None
    except HttpError as error:
        print(f"An error occurred while searching for folder: {error}")
        return None


if __name__ == '__main__':

    # Authenticate
    creds = authenticate_google_drive()
    if not creds:
        print("Authentication failed")
        raise GoogleAuthenticationFailure

    # Build Drive Service
    service = build_drive_service(creds)
    if not service:
        print("Failed to build Drive service")
        raise GoogleServiceBuildFailure

    # get all files and folders
    if os.path.exists(DRIVE_JSON):
        master_dict = Dictionary(json_source=DRIVE_JSON)
    else:
        master_dict = build_dict_from_folder(service, "images 3.0")
        master_dict.write(DRIVE_JSON)


    # delete .DS_Store files from Mac
    print(f'checking for .DS_Store files, Mac artifact')
    file_name = '.DS_Store'
    file_ids = master_dict['name_id'].get(file_name)
    if file_ids is not None and len(file_ids):
        for id in file_ids:
            delete_file(service, file_name, id)
    master_dict.remove_key(file_name)
    master_dict.write(DRIVE_JSON)

    # check for images larger than 100k
    print(f'checking for image files larger than 100kb in {IMAGES_FOLDER}')
    results = master_dict[IMAGES_FOLDER].recursive_get_key('size')
    for result in results:
        if int(result[2]) > 100000:
            print(result)

    # check for the correct number of images
    print(f'checking for correct number of images (427)')
    loc_speed_nums = []
    for dir in [-1, 1]:
        for speed in range(3, 11):
            results = master_dict[IMAGES_FOLDER].recursive_get_key(str(dir * speed))
            loc_speed_nums.extend([(ls[0].split(' ')[0], int(ls[0].split(' ')[2]), len(ls[2].keys()) - 1) for ls in results])
    loc_speed_nums.sort()
    for lsn in loc_speed_nums:
        if lsn[2] != 427:
            print(f'** {lsn}')

    # create google urls csv file
    print('creating csv file {GOOGLE_URLS_CSV}')
    results = master_dict[IMAGES_FOLDER].recursive_get_key('mimeType')  # XXX-graphs > speed > filename > 'mimetype', 'mimeType', actual mimeType
    image_names = [result[0].split(' > ')[2] for result in results if result[2] == PNG_MIMETYPE]  # filename => loc speed year month day.png

    loc_speeds = list(set([(img.split(' ')[0],  int(img.split(' ')[1])) for img in image_names]))
    loc_speeds.sort()
    loc_speeds = [f'{ls[0]} {ls[1]}' for ls in loc_speeds]

    dates = list(set([(int(img.split(' ')[2]), int(img.split(' ')[3]), int(img.split(' ')[4].split('.')[0])) for img in image_names]))
    dates.sort()
    dates = [f'{d[1]}/{d[2]}/{d[0]}' for d in dates]

    dates_dictionary = Dictionary({date: {'date': date} for date in dates})
    for img in image_names:
        loc_speed = f'{img.split(' ')[0]} {int(img.split(' ')[1])}'
        date = f'{int(img.split(' ')[3])}/{int(img.split(' ')[4].split('.')[0])}/{int(img.split(' ')[2])}'
        dates_dictionary[date][loc_speed] = f'{CSV_PREFIX}{master_dict['name_id'].get(img)[0]}{CSV_SUFFIX}'

    image_frame = DataFrame(columns=['date'] + loc_speeds)
    for date in dates:
        image_frame.loc[len(image_frame)] = dates_dictionary[date]
    image_frame.write(GOOGLE_URLS_CSV)

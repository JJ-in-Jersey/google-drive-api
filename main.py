import os
from operator import itemgetter
from statistics import mean
from pathlib import Path
from scipy.stats import zscore
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

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
TYPE_DICT = {'graphs': {'size': 100000, 'z': 3}, 'tables': {'size': 10000, 'z': 4.7}}


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
    print(f'deleting File ({file_name}: {file_id})')
    try:
        service.files().delete(fileId=file_id).execute()
        print(f"File ({file_name}: {file_id}) deleted successfully.")
    except HttpError as error:
        print(f"An error occurred while deleting file: {error}")


def get_drive_items(service, parent_id=None):
    """
    Retrieves files and folders for a given parent ID.
    If parent_id is None, it gets items from My Drive (root).
    """
    items = []
    token = None
    # Query to get children of a specific folder ID or 'root' (My Drive)
    # and exclude trashed items.
    query = f"'{parent_id}' in parents and trashed = false" if parent_id else "'root' in parents and trashed = false"

    while True:
        try:
            # Request only the fields essential for building the tree: id, name, mimeType, parents
            response = service.files().list(q=query, spaces='drive',
                                            fields='nextPageToken, files(id, name, size, mimeType)', pageToken=token).execute()
            items.extend(response.get('files', []))
            token = response.get('nextPageToken', None)
            if not token:
                break  # No more pages, exit loop
        except HttpError as error:
            print(f'An error occurred while listing files: {error}')
            break  # Exit on error
    return items


def build_file_tree(service, start_folder_id: str = 'root', _path='', _progress: dict = None, _depth: int = 0, _parent_path: str = None):
    """
    recursively builds a Dictionary representing the Google Drive file tree
    :param service: authenticated Google Drive API service object
    :param start_folder_id: ID of the starting folder; none returns entire drive (root)
    :param _path: internal parameter for tracking current path
    :param _progress: internal parameter for tracking progress
    :param _depth: internal parameter for tracking indentation depth
    :param _parent_path: internal parameter for tracking parent folder name
    :return: Dictionary mirroring the Google Drive file tree
    """
    # Initialize progress tracking on first call
    if _progress is None:
        _progress = {'folders': 0, 'files': 0, 'current_folder': ''}
        print("🚀 building Google Drive file tree")

    _progress['current_folder'] = _path
    indent = " " * _depth

    tree = Dictionary()
    items = get_drive_items(service, start_folder_id)

    for item in items:

        if item['mimeType'] == FOLDER_MIMETYPE:
            # If it's a folder, recursively call build_file_tree for its contents
            _progress['folders'] += 1

            _path = f'{_parent_path}/{item['name']}' if _parent_path else item['name']
            tree[item['name']] = Dictionary({'_path': _path, '_id': item['id'], '_mimeType': item['mimeType']})

            # Count items in this folder before processing
            folder_items = get_drive_items(service, item['id'])
            folder_count = sum(1 for i in folder_items if i['mimeType'] == FOLDER_MIMETYPE)
            file_count = len(folder_items) - folder_count

            # Display parent/leaf folder with stats
            if _parent_path:
                print(f"{indent}📁 {_parent_path}/{item['name']} ({folder_count} folders, {file_count} files)")
            else:
                print(f"{indent}📁 {item['name']} ({folder_count} folders, {file_count} files)")

            # Add folder contents directly to the tree, merging with the current level
            folder_contents = build_file_tree(service, item['id'], _path, _progress, _depth + 1, _path)  # Recursive call with current folder as parent
            tree[item['name']].update(folder_contents)
            pass

        else:
            # If it's a file, add its details
            _progress['files'] += 1
            name = item.pop('name')
            tree[name] = Dictionary({'_' + k: v for k, v in item.items()})
            tree[name]['_path'] = f'{_parent_path}/{name}'

    # Print summary when back at root
    if _path == 'drive':
        print(f"✅ Complete! Total: {_progress['folders']} folders, {_progress['files']} files")

    return tree


def get_folder_id_by_name(service, target_name: str):
    """
    retrieves the folder ID for a given folder name
    :param service: authenticated Google Drive API service object
    :param folder_name (str): target folder name
    :return: id of the target folder
    """
    try:
        # Query for folders with the given name and whose parent is 'root' (My Drive)
        query = f"name = '{target_name}' and mimeType = 'application/vnd.google-apps.folder' and 'root' in parents and trashed=false"
        response = service.files().list(q=query, spaces='drive', fields='files(id, name, parents)').execute()
        folders = response.get('files', [])
        if folders:
            print(f"Found top-level folder '{target_name}' with ID: {folders[0]['id']}")
            return folders[0]['id']  # Return the ID of the first matching folder
        else:
            print(f"Folder '{target_name}' not found at the highest level of your Drive.")
            return None
    except HttpError as error:
        print(f"An error occurred while searching for folder: {error}")
        return None


def get_all_folders_flat(service):
    """
    Retrieves a flat list of ALL folders (not files) from My Drive and its subfolders.
    """
    all_folders = []
    page_token = None
    # Query for all folders, recursively across the entire Drive
    query = "mimeType = 'application/vnd.google-apps.folder' and trashed = false"

    while True:
        try:
            response = service.files().list(
                q=query,
                spaces='drive',
                fields='nextPageToken, files(id, name, parents)',  # Need parents to build the tree
                pageToken=page_token
            ).execute()
            all_folders.extend(response.get('files', []))
            page_token = response.get('nextPageToken', None)
            if not page_token:
                break
        except HttpError as error:
            print(f'An error occurred while listing all folders: {error}')
            break
    return all_folders


if __name__ == '__main__':

    # authenticate
    creds = authenticate_google_drive()
    if not creds:
        print("Authentication failed")
        raise GoogleAuthenticationFailure

    # build drive service
    service = build_drive_service(creds)
    if not service:
        print("Failed to build Drive service")
        raise GoogleServiceBuildFailure

    # build dictionary
    if os.path.exists(DRIVE_JSON):
        master_dict = Dictionary(json_source=DRIVE_JSON)
    else:
        images_folder_id = get_folder_id_by_name(service, IMAGES_FOLDER)
        master_dict = build_file_tree(service, images_folder_id)
        master_dict.write(DRIVE_JSON)

    # delete .DS_Store files from Mac
    file_name = 'delete_me.rtf'
    print(f'\nchecking for {file_name} files, Mac artifact')
    keys = master_dict.find_keys(file_name)
    if keys:
        for key in keys:
            master_dict.del_key(key[0])
            delete_file(service, key[0].rsplit('/', 1)[0], key[1]['_id'])
        master_dict.write(DRIVE_JSON)

    # list locations
    print(f'locations available on Google Drive')
    for type in TYPE_DICT.keys():
        if master_dict.get(type):
            for loc in sorted([loc for loc in master_dict[type].keys() if loc[0] != '_']):
                print(f'  {loc}')

    # check for large files
    for type in TYPE_DICT.keys():
        if master_dict.get(type):
            print(f'checking for image files larger than {TYPE_DICT[type]['size']} kb in [{IMAGES_FOLDER}][{type}]')
            for r in master_dict[type].find_keys('_size'):
                if int(r[1]) > TYPE_DICT[type]['size']:
                    print(f' ** {r}')

    # check for the correct number of images
    print(f'checking for correct number of images (427)')
    loc_speed_count = []
    print(f' ', end='')
    for sign in [-1, 1]:
        for speed in range(3, 11):
            print(f'{sign * speed}  ', end='')
            for r in master_dict.find_keys(str(sign * speed)):
                length = len([k for k in r[1].keys() if k[0] != '_' and r[1][k]['_mimeType'] == PNG_MIMETYPE])
                loc_speed_count.append((r[0].rsplit('/', 1)[0], int(r[0].split('/')[-1]), length))
    print('')
    for lsc in sorted(loc_speed_count, key=itemgetter(0, 1)):
        if lsc[2] != 427:
            print(f' ***  {lsc[0]}/{lsc[1]} {lsc[2]}')

    # check for unusually large or small images
    for type in TYPE_DICT.keys():
        if master_dict.get(type):
            print(f'checking for unusually large or small images in [{IMAGES_FOLDER}][{type}]')
            file_sizes = [fs for fs in master_dict[type].find_keys('_size') if master_dict.parent(fs[0])['_mimeType'] == PNG_MIMETYPE]
            average = int(round(mean([int(fs[1]) for fs in file_sizes])))
            z_scores = [round(zs, 2) for zs in zscore([fs[1] for fs in file_sizes])]
            outliers = [(fs[0].rsplit('/', 1)[0], fs[1], z_scores[i]) for i, fs in enumerate(file_sizes) if abs(z_scores[i]) > TYPE_DICT[type]['z']]
            print(f'\n{type}')
            for ol in outliers:
                print(f'  path: {ol[0]}  size: {ol[1]}  ave: {average}  z: {ol[2]} ({TYPE_DICT[type]['z']})')

    # create google urls csv file
    print('creating csv file {GOOGLE_URLS_CSV}')
    columns = Dictionary()
    results = master_dict.find_keys('_mimeType', PNG_MIMETYPE)
    for r in results:
        fields = r[0].split('/')
        id = master_dict.parent(r[0])['_id']
        file_name = fields[3][:-4]
        ymd = file_name.split()[2:]  # year, month, day
        date = f'{ymd[0]}/{ymd[1]}/{ymd[2]}'
        column_name = f'{fields[1]} {fields[2]}'
        columns.setdefault(column_name, {})
        columns[column_name][date] = f'{CSV_PREFIX}{id}{CSV_SUFFIX}'

    columns_list = list(columns.keys())
    columns_list.sort(key=lambda x: (x.split()[0], int(x.split()[1])))

    columns = Dictionary({key: columns[key] for key in columns_list})
    for k, v in columns.items():
        columns[k] = Dictionary({key: v[key] for key in sorted(v)})

    image_frame = DataFrame(columns)
    image_frame.insert(0, 'date', value=None)
    image_frame['date'] = image_frame.index
    image_frame['date'] = image_frame['date'].apply(lambda x: f'{x.split('/')[1]}/{x.split('/')[2]}/20{x.split('/')[0]}')
    image_frame.reset_index(drop=True, inplace=True)
    image_frame.write(GOOGLE_URLS_CSV)

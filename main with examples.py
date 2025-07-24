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

# Define the scopes required for Google Drive API access.
# 'https://www.googleapis.com/auth/drive' gives full access to Google Drive.
# For more restricted access, you might use 'https://www.googleapis.com/auth/drive.file'
# which only allows access to files created or opened by the app.
SCOPES = ['https://www.googleapis.com/auth/drive']
JSON = Path('google_drive.json')
CSV_PREFIX = 'https://drive.google.com/file/d/'
CSV_POSTFIX = '/view?usp=drive_link'
FOLDER_MIMETYPE = 'application/vnd.google-apps.folder'
PNG_MIMETYPE = 'image/png'
FILE_MIMETYPE = 'application/vnd.google-apps.file'


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
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # The client_secrets.json file contains your OAuth 2.0 client ID and client secret.
            # You download this from the Google Cloud Console.
            flow = InstalledAppFlow.from_client_secrets_file(
                'client_secrets.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
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


# def list_files(service):
#     """
#     Lists the first 10 files and folders in the user's Google Drive.
#     """
#     print("\n--- Listing Files and Folders ---")
#     try:
#         # Call the Drive v3 API to list files.
#         # q: query for files (e.g., 'mimeType = "image/jpeg"').
#         # pageSize: number of items to return.
#         # fields: specifies which fields to return in the response.
#         results = service.files().list(
#             pageSize=1000, fields="nextPageToken, files(id, name, mimeType)",
#             q="'root' in parents and mimeType = 'application/vnd.google-apps.folder'").execute()
#         items = results.get('files', [])
#
#         if not items:
#             print('No files found.')
#             return
#         print('Files:')
#         for item in items:
#             print(f"{item['name']} ({item['id']}) - Type: {item['mimeType']}")
#     except HttpError as error:
#         print(f"An error occurred while listing files: {error}")
#
#
# def upload_file(service, file_path, folder_id=None):
#     """
#     Uploads a file to Google Drive.
#     Args:
#         service: The Google Drive API service object.
#         file_path: The local path to the file to upload.
#         folder_id: (Optional) The ID of the folder to upload the file into.
#                    If None, the file is uploaded to the root directory.
#     Returns:
#         The uploaded file's ID if successful, None otherwise.
#     """
#     print(f"\n--- Uploading File: {os.path.basename(file_path)} ---")
#     try:
#         file_metadata = {'name': os.path.basename(file_path)}
#         if folder_id:
#             file_metadata['parents'] = [folder_id]
#
#         media = MediaFileUpload(file_path, resumable=True)
#         file = service.files().create(body=file_metadata, media_body=media,
#                                       fields='id, name').execute()
#         print(f"File '{file.get('name')}' uploaded. File ID: {file.get('id')}")
#         return file.get('id')
#     except HttpError as error:
#         print(f"An error occurred while uploading file: {error}")
#         return None
#
#
# def download_file(service, file_id, destination_path):
#     """
#     Downloads a file from Google Drive.
#     Args:
#         service: The Google Drive API service object.
#         file_id: The ID of the file to download.
#         destination_path: The local path where the file should be saved.
#     """
#     print(f"\n--- Downloading File (ID: {file_id}) to {destination_path} ---")
#     try:
#         request = service.files().get_media(fileId=file_id)
#         file_handle = io.BytesIO()
#         downloader = MediaIoBaseDownload(file_handle, request)
#         done = False
#         while done is False:
#             status, done = downloader.next_chunk()
#             print(f"Download progress: {int(status.progress() * 100)}%.")
#
#         # Write the downloaded content to the specified destination path
#         with open(destination_path, 'wb') as f:
#             f.write(file_handle.getvalue())
#         print(f"File downloaded successfully to {destination_path}")
#     except HttpError as error:
#         print(f"An error occurred while downloading file: {error}")
#
#
# def update_file(service, file_id, new_name=None, new_mime_type=None):
#     """
#     Updates a file's metadata (e.g., name or MIME type) on Google Drive.
#     Args:
#         service: The Google Drive API service object.
#         file_id: The ID of the file to update.
#         new_name: (Optional) The new name for the file.
#         new_mime_type: (Optional) The new MIME type for the file.
#     Returns:
#         The updated file's ID if successful, None otherwise.
#     """
#     print(f"\n--- Updating File (ID: {file_id}) ---")
#     try:
#         file_metadata = {}
#         if new_name:
#             file_metadata['name'] = new_name
#         if new_mime_type:
#             file_metadata['mimeType'] = new_mime_type
#
#         # Use update method to patch the file metadata.
#         updated_file = service.files().update(
#             fileId=file_id,
#             body=file_metadata,
#             fields='id, name, mimeType'
#         ).execute()
#         print(f"File updated. New Name: {updated_file.get('name')}, New Type: {updated_file.get('mimeType')}")
#         return updated_file.get('id')
#     except HttpError as error:
#         print(f"An error occurred while updating file: {error}")
#         return None


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


# def create_folder(service, folder_name, parent_folder_id=None):
#     """
#     Creates a new folder on Google Drive.
#     Args:
#         service: The Google Drive API service object.
#         folder_name: The name of the new folder.
#         parent_folder_id: (Optional) The ID of the parent folder.
#                           If None, the folder is created in the root directory.
#     Returns:
#         The created folder's ID if successful, None otherwise.
#     """
#     print(f"\n--- Creating Folder: {folder_name} ---")
#     try:
#         file_metadata = {
#             'name': folder_name,
#             'mimeType': 'application/vnd.google-apps.folder'
#         }
#         if parent_folder_id:
#             file_metadata['parents'] = [parent_folder_id]
#
#         folder = service.files().create(body=file_metadata, fields='id, name').execute()
#         print(f"Folder '{folder.get('name')}' created. Folder ID: {folder.get('id')}")
#         return folder.get('id')
#     except HttpError as error:
#         print(f"An error occurred while creating folder: {error}")
#         return None
#
#
# def get_all_from_root(service):
#     """Fetches all files and folders from Google Drive."""
#     items = []
#     page_token = None
#     while True:
#         try:
#             # Query for files and folders, specifying fields for efficiency
#             response = service.files().list(
#                 q="trashed=false",  # Exclude trashed items
#                 spaces='drive',
#                 fields='nextPageToken, files(id, name, mimeType, parents, size)',
#                 pageToken=page_token
#             ).execute()
#             items.extend(response.get('files', []))
#             page_token = response.get('nextPageToken', None)
#             print(f'Got {len(items)} files from Google Drive.')
#             if not page_token:
#                 break
#         except HttpError as error:
#             print(f"An error occurred while fetching files: {error}")
#             break
#     return items


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
            indent += ' ' * max_name_length - len(current_folder_name)

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


def main():

    # Authenticate
    creds = authenticate_google_drive()
    if not creds:
        print("Authentication failed. Exiting.")
        return

    # Build Drive Service
    service = build_drive_service(creds)
    if not service:
        print("Failed to build Drive service. Exiting.")
        return

    # get all files and folders
    if os.path.exists(JSON):
        master_dict = Dictionary(json_source=JSON)
    else:
        master_dict = build_dict_from_folder(service, "images 3.0")
        master_dict.write(JSON)


    # delete .DS_Store files from Mac
    print(f'checking for .DS_Store files, Mac artifact')
    file_name = '.DS_Store'
    file_ids = master_dict['name_id'].get(file_name)
    if file_ids is not None and len(file_ids):
        # for id in file_ids:
        #     delete_file(service, file_name, id)
        master_dict.remove_key(file_name)
        master_dict.write(JSON)

    image_folder = 'images 3.0'
    # check for images larger than 100k
    print(f'checking for image files larger than 100kb')
    results = master_dict[image_folder].recursive_get_key('size')
    for result in results:
        if int(result[2]) > 100000:
            print(result)

    # check for the correct number of images
    print(f'checking for correct number of images (427)')

    loc_speed_nums = []
    for dir in [-1, 1]:
        for speed in range(3, 11):
            results = master_dict[image_folder].recursive_get_key(str(dir * speed))
            loc_speed_nums.extend([(ls[0].split(' ')[0], int(ls[0].split(' ')[2]), len(ls[2].keys()) - 1) for ls in results])
    loc_speed_nums.sort()
    for lsn in loc_speed_nums:
        if lsn[2] != 427:
            print(f'** {lsn}')
        else:
            print(f'{lsn}')

    # 3. List Files
    # list_files(service)

    # # 4. Create a fake file for upload and download
    # dummy_file_name = "my_dummy_file.txt"
    # with open(dummy_file_name, "w") as f:
    #     f.write("This is a test file created by the Google Drive API script.")
    # print(f"\nCreated local dummy file: {dummy_file_name}")
    #
    # # 5. Upload a file
    # uploaded_file_id = upload_file(service, dummy_file_name)
    #
    # if uploaded_file_id:
    #     # 6. Download the uploaded file
    #     downloaded_file_name = "downloaded_dummy_file.txt"
    #     download_file(service, uploaded_file_id, downloaded_file_name)
    #
    #     # 7. Update the uploaded file (rename it)
    #     updated_file_id = update_file(service, uploaded_file_id, new_name="renamed_dummy_file.txt")
    #
    #     # 8. Delete the updated file
    #     if updated_file_id:
    #         delete_file(service, updated_file_id)
    #
    # # Clean up the local fake files
    # if os.path.exists(dummy_file_name):
    #     os.remove(dummy_file_name)
    # if os.path.exists(downloaded_file_name):
    #     os.remove(downloaded_file_name)
    # print(f"\nCleaned up local dummy files: {dummy_file_name}, {downloaded_file_name}")
    #
    # # 9. Create a folder
    # new_folder_id = create_folder(service, "My New API Folder")
    #
    # # 10. Upload a file into the newly created folder (optional)
    # if new_folder_id:
    #     another_dummy_file = "another_dummy.txt"
    #     with open(another_dummy_file, "w") as f:
    #         f.write("This file is inside the new folder.")
    #     print(f"\nCreated local dummy file for folder: {another_dummy_file}")
    #     upload_file(service, another_dummy_file, folder_id=new_folder_id)
    #     os.remove(another_dummy_file)
    #     print(f"Cleaned up local dummy file: {another_dummy_file}")
    #
    #     # 11. Delete the created folder (and its contents)
    #     # Be careful when deleting folders, as it deletes all contents!
    #     # For demonstration, we'll delete it. In a real app, you might not.
    #     delete_file(service, new_folder_id)  # Folders are also 'files' in the API context

    print("\n--- All operations completed ---")


if __name__ == '__main__':
    main()

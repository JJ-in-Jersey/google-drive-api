from pathlib import Path
from tt_file_tools.file_tools import GoogleDriveTree, OSFileTree
import os

from tt_google_drive.google_drive import GoogleDrive

# Define the scopes required for Google Drive API access.
# 'https://www.googleapis.com/auth/drive' gives full access to Google Drive.
# For more restricted access, you might
# use 'https://www.googleapis.com/auth/drive.file'
# which only allows access to files created or opened by the app.
DRIVE_JSON = Path('google_drive.json')
FILE_JSON = Path('files.json')
CSV_PREFIX = 'https://drive.google.com/file/d/'
CSV_SUFFIX = '/view?usp=drive_link'
FOLDER_MIMETYPE = 'application/vnd.google-apps.folder'
PNG_MIMETYPE = 'image/png'
FILE_MIMETYPE = 'application/vnd.google-apps.file'
IMAGES_FOLDER = 'images 3.0'
FILES_FOLDER = '/users/jason/fair currents/find_test'
GOOGLE_URLS_CSV = 'google_urls.csv'


if __name__ == '__main__':

    # # build dictionary
    # if os.path.exists(DRIVE_JSON):
    #     drive_tree = GoogleDriveTree(json_source=DRIVE_JSON)
    # else:
    #     drive_tree = GoogleDriveTree(start_path=IMAGES_FOLDER)
    #     drive_tree.write(DRIVE_JSON)

    # build dictionary
    if os.path.exists(FILE_JSON):
        drive_tree = OSFileTree(json_source=FILE_JSON)
    else:
        drive_tree = OSFileTree(start_path=FILES_FOLDER)
        drive_tree.write(FILE_JSON)

    # delete .DS_Store files from Mac
    file_name = '.DS_Store'
    print(f'\nchecking for {file_name} files, Mac artifact')
    keys = drive_tree.find_keys(file_name)
    for key in keys:
        drive_tree.drive.delete_file(key[1]['id'])
        drive_tree.del_key(key[0])
        drive_tree.drive.delete_file(service, key[0].rsplit('/', 1)[0], key[1]['_id'])
    #     master_dict.write(DRIVE_JSON)
    #
    # # list locations
    # print(f'locations available on Google Drive')
    # for type in TYPE_DICT.keys():
    #     if master_dict.get(type):
    #         for loc in sorted([loc for loc in master_dict[type].keys() if loc[0] != '_']):
    #             print(f'  {loc}')
    #
    # # check for large files
    # for type in TYPE_DICT.keys():
    #     if master_dict.get(type):
    #         print(f'checking for image files larger than {TYPE_DICT[type]['size']} kb in [{IMAGES_FOLDER}][{type}]')
    #         for r in master_dict[type].find_keys('_size'):
    #             if int(r[1]) > TYPE_DICT[type]['size']:
    #                 print(f' ** {r}')
    #
    # # check for the correct number of images
    # print(f'checking for correct number of images (427)')
    # loc_speed_count = []
    # print(f' ', end='')
    # for sign in [-1, 1]:
    #     for speed in range(3, 11):
    #         print(f'{sign * speed}  ', end='')
    #         for r in master_dict.find_keys(str(sign * speed)):
    #             length = len([k for k in r[1].keys() if k[0] != '_' and r[1][k]['_mimeType'] == PNG_MIMETYPE])
    #             loc_speed_count.append((r[0].rsplit('/', 1)[0], int(r[0].split('/')[-1]), length))
    # print('')
    # for lsc in sorted(loc_speed_count, key=itemgetter(0, 1)):
    #     if lsc[2] != 427:
    #         print(f' ***  {lsc[0]}/{lsc[1]} {lsc[2]}')
    #
    # # check for unusually large or small images
    # for type in TYPE_DICT.keys():
    #     if master_dict.get(type):
    #         print(f'checking for unusually large or small images in [{IMAGES_FOLDER}][{type}]')
    #         file_sizes = [fs for fs in master_dict[type].find_keys('_size') if master_dict.parent(fs[0])['_mimeType'] == PNG_MIMETYPE]
    #         average = int(round(mean([int(fs[1]) for fs in file_sizes])))
    #         z_scores = [round(zs, 2) for zs in zscore([fs[1] for fs in file_sizes])]
    #         outliers = [(fs[0].rsplit('/', 1)[0], fs[1], z_scores[i]) for i, fs in enumerate(file_sizes) if abs(z_scores[i]) > TYPE_DICT[type]['z']]
    #         print(f'\n{type}')
    #         for ol in outliers:
    #             print(f'  path: {ol[0]}  size: {ol[1]}  ave: {average}  z: {ol[2]} ({TYPE_DICT[type]['z']})')
    #
    # # create google urls csv file
    # print(f'creating csv file {GOOGLE_URLS_CSV}')
    # columns = Dictionary()
    # results = master_dict.find_keys('_mimeType', PNG_MIMETYPE)
    # for r in results:
    #     fields = r[0].split('/')
    #     id = master_dict.parent(r[0])['_id']
    #     file_name = fields[3][:-4]
    #     ymd = file_name.split()[2:]  # year, month, day
    #     date = f'{ymd[0]}/{ymd[1]}/{ymd[2]}'
    #     column_name = f'{fields[1]} {fields[2]}'
    #     columns.setdefault(column_name, {})
    #     columns[column_name][date] = f'{CSV_PREFIX}{id}{CSV_SUFFIX}'
    #
    # columns_list = list(columns.keys())
    # columns_list.sort(key=lambda x: (x.split()[0], int(x.split()[1])))
    #
    # columns = Dictionary({key: columns[key] for key in columns_list})
    # for k, v in columns.items():
    #     columns[k] = Dictionary({key: v[key] for key in sorted(v)})
    #
    # image_frame = DataFrame(columns)
    # image_frame.insert(0, 'date', value=None)
    # image_frame['date'] = image_frame.index
    # image_frame['date'] = image_frame['date'].apply(lambda x: f'{x.split('/')[1]}/{x.split('/')[2]}/20{x.split('/')[0]}')
    # image_frame.reset_index(drop=True, inplace=True)
    # image_frame.write(GOOGLE_URLS_CSV)

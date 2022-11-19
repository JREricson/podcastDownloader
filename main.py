#!/usr/bin/env python3
import os
import sys
import traceback

from bs4 import BeautifulSoup as bs
import requests
import logging
from os import path
from pathlib import Path
import pickle
from pprint import pprint
DEBUG = True

# ATTENTION: Change below to set different directory to save files into.
SAVE_DIRECTORY = path.join(
    str(Path.home()), 'Downloads/Podcasts/podcast_downloader')
SAVED_PODCASTS_FILE_NAME = 'saved_podcasts.txt'
SAVED_PODCASTS_FILE_PATH = os.path.join(
    SAVE_DIRECTORY, SAVED_PODCASTS_FILE_NAME)
EXCLUDE_LIST_PATH = os.path.join(
    SAVE_DIRECTORY, 'exclude_list.pkl')
# ATTENTION: Change below to set different minimum disk space.
MIN_SPACE_ALLOWED_MB = 5*1024
logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s',
    filename= path.join(SAVE_DIRECTORY,'podcast.log'), level=logging.INFO,
     datefmt='%Y-%m-%d %H:%M:%S')


def convert_date_to_YYYYMMDD_date(date_string):
    """Converts date

    Args:
        date_string (str): Date in formate like <Sun, 6 Mar 2022 19:08:44 PST> commonly found in RSS feeds.

    Returns:
        str: Date in YYYYMMDD format
    """
    date_parts = date_string.split()

    if len(date_parts[1]) == 1:
        date_parts[1] = '0' + date_parts[1]

    new_date_string = date_parts[3] + '-' + \
        get_month_num(date_parts[2]) + '-' + date_parts[1]
    return new_date_string


def get_month_num(month: str) -> str:
    month = str.lower(month)
    if (month[0:2] == 'ja'):
        return '01'
    elif (month[0] == 'f'):
        return '02'
    elif (month[0:3] == 'mar'):
        return '03'
    elif (month[0] == 'a'):
        return '04'
    elif (month[0:3] == 'may'):
        return '05'
    elif (month[0:3] == 'jun'):
        return '06'
    elif (month[0:3] == 'jul'):
        return '07'
    elif (month[0:3] == 'aug'):
        return '08'
    elif (month[0:3] == 'sep'):
        return '09'
    elif (month[0:3] == 'oct'):
        return '10'
    elif (month[0:3] == 'nov'):
        return '11'
    elif (month[0:3] == 'dec'):
        return '12'
    else:
        raise ValueError('failed to convert date')


def get_renamed_podcast_titles_and_audio_urls(rss_url):
    """Collects the podcast title and download link from the rss_url provided. The files will be renamed with the date in YYYYMMDD format coming before the original title name.

    Args:
        rss_url (string): _description_

    Returns:
        [][]: a nested list, where each entry is is in the from of [<newly named podcast title>, <url where podcast is found>]
    """

    source = requests.get(rss_url, timeout=3).text
    soup = bs(source, 'lxml')
    items = soup('item')
    podcast_details = []
    for item in items:
        # item details
        title = item.title.text
        pub_date = item.pubdate.text
        audioUrl = item.enclosure['url']

        # renaming item and adding to list
        convertedDate = convert_date_to_YYYYMMDD_date(pub_date)
        podcast_details.append(
            (convertedDate + '_' + title + '.mp3', audioUrl))
    return podcast_details


def ensure_exclude_list_exists():
    """ A list of file to ignore from the RSS  feed is stored in a dictionary saved as a pickle file. This function ensures tht file exists by creating an empty dictionary if none is present
    """

    if not path.isfile(EXCLUDE_LIST_PATH):
        empty_dict = {}
        with open(EXCLUDE_LIST_PATH, "wb") as exclude_file:
            pickle.dump(empty_dict, exclude_file)
            logging.info('No exclude list was present, so one was created')


def get_podcasts_to_exclude_by_exclusion_date(podcast_details, exclude_before_date):
    exclude_list = []
    for pcTitle, _ in podcast_details:
        if pcTitle[:10] < exclude_before_date:
            exclude_list.append(pcTitle)

    return exclude_list


def get_filtered_podcast_download_list(podcast_name, podcast_details, exclude_before_date):
    """Returns list of podcast detail for podcasts that are in the in the saved exclude list or before the exclude by date if it is the first time checking for that podcast.

    """
    exclude_dict = None
    with (open(EXCLUDE_LIST_PATH, "rb")) as exclude_file:
        exclude_dict = pickle.load(exclude_file)

       
        if not podcast_name in exclude_dict:
            podcasts_to_exclude = get_podcasts_to_exclude_by_exclusion_date(
                podcast_details, exclude_before_date)
            exclude_dict[podcast_name] = podcasts_to_exclude

        filtered_podcast_details = list(
            filter(lambda pc: pc[0] not in exclude_dict[podcast_name], podcast_details))

    with (open(EXCLUDE_LIST_PATH, "wb")) as exclude_file:
        pickle.dump(exclude_dict, exclude_file, -1)
        logging.info(f'Files from RSS feed that will NOT be downloaded for <{podcast_name}> are: <{exclude_dict[podcast_name]}>')
        logging.info(f'Files from RSS feed that WILL be downloaded for <{podcast_name}> are: <{filtered_podcast_details}>')
        return filtered_podcast_details


def download_file(url, filename, download_chunk_size=10 * 1024 * 1024):
    with requests.get(url, stream=True) as req:
        logging.info(f'Attempting to download <{filename}>')
        req.raise_for_status()
        file_size_MB = int(req.headers['Content-Length'])/1024**2
        logging.info(f'Size of file to be downloaded {file_size_MB}')
        statvfs_diskspace_tool = os.statvfs('/')
        disc_space_left_MB = (
            statvfs_diskspace_tool.f_bavail * statvfs_diskspace_tool.f_frsize) / 1024**2

        hard_disk_space_after_download_MB = disc_space_left_MB-file_size_MB

        logging.info(
            f'Disk space after download will be completed: {hard_disk_space_after_download_MB} MB.\tMin space allowed on file system: {MIN_SPACE_ALLOWED_MB} MB.')
        if hard_disk_space_after_download_MB < MIN_SPACE_ALLOWED_MB:
            raise OSError(
                f'Program only downloads when there is more than {MIN_SPACE_ALLOWED_MB/1024} GB of hd space remaining. Remaining space is <{hard_disk_space_after_download_MB}>')
        with open(filename,
                  'wb',
                  ) as new_audio_file:
            for chunk in req.iter_content(chunk_size=download_chunk_size):
                new_audio_file.write(chunk)
        logging.info(f'Download of <{filename}> is complete')


def download_podcasts_from_rss_url(podcast_name, podcast_rss_url, exclude_before_date):
    # TODO autoformat subDirectory to dir that is legal and without spaces
    logging.info(f'Looking up information for <{podcast_name}> from url<{podcast_rss_url}>')
    # creating directories for podcast in system
    sub_directory = path.join(SAVE_DIRECTORY, podcast_name)
    if not os.path.exists(sub_directory):
        logging.info(f'created new directory at <{sub_directory}>')
        os.makedirs(sub_directory)
    os.chdir(sub_directory)

    podcast_details = get_renamed_podcast_titles_and_audio_urls(
        podcast_rss_url)
    DEBUG and pprint(podcast_details)
    podcasts_to_download = get_filtered_podcast_download_list(
        podcast_name, podcast_details, exclude_before_date)

    for podcast_title, url in podcasts_to_download:
        download_file(url, podcast_title)
        add_podcast_title_to_exclude_file(podcast_name, podcast_title)


def download_file_or_raise_error(file):
    try:
        download_file(file)
    except OSError as e:
        msg = f'Error: Could not complete download.\n{e,traceback.format_exc()}'
        logging.error(msg)
    except Exception:
        raise Exception(f'Error: Could not complete download.\n{traceback.format_exc()}'
                        )


def add_podcast_title_to_exclude_file(podcast_name, podcast_title):
    with (open(EXCLUDE_LIST_PATH, "rb")) as exclude_file:
        exclude_dict = pickle.load(exclude_file)
        exclude_dict[podcast_name].append(podcast_title)
    with (open(EXCLUDE_LIST_PATH, "wb")) as exclude_file:
        pickle.dump(exclude_dict, exclude_file, -1)
        logging.info(f'Exclude file has been updated. <{podcast_name}> has the title of <{podcast_title}> added to the exclusion list')


def get_list_of_podcasts(directory):
    podcasts = []
    podcast_filename = path.join(directory, 'podcastTitles.txt')
    with open(podcast_filename, 'r') as pc_file:
        for line in pc_file.readlines():
            split = line.split('\t')
            podcast = split[0].strip()
            url = split[1].strip()
            podcasts.append((podcast, url))

    return podcasts


def ensure_dir_exists(dir):

    if not path.isdir(dir):
        Path(dir).mkdir(parents=True)


def get_podcast_to_download_details_from_file():
    podcast_details = []
    with open(SAVED_PODCASTS_FILE_PATH, 'r') as f:
        for line in f:
            single_podcast_detail = [x.strip() for x in line.split('\t')]
            podcast_details.append(single_podcast_detail)
    return podcast_details


def run_program():
    logging.info('Starting program...')
    ensure_exclude_list_exists()
    podcast_detail_list = get_podcast_to_download_details_from_file()
    for pc in podcast_detail_list:
        download_podcasts_from_rss_url(*pc)

    DEBUG and print(f'saving podcasts in: {SAVE_DIRECTORY}')


if __name__ == '__main__':

    if len(sys.argv) == 1:
        run_program()
    else:
        arg1 = sys.argv[1].lower()
        if arg1 == 'add' or arg1 == 'a':
            podcast_name = input("Enter name of podcast: ")
            rss_url = input("Enter the rss feed xml url: ")
            print('The program will download all podcasts after the start date specified')
            exclude_before_date = input(
                'Please enter a start date in YYYY-MM-DD format: ')

            # TODO could make a check to see if podcast is already in list
            # TODO add format validators to user input
            with open(SAVED_PODCASTS_FILE_PATH, 'a+') as f:
                f.write(f'{podcast_name}\t{rss_url}\t{exclude_before_date}\n')
        elif arg1 == 'h' or arg1 == 'help' or arg1 == '-h' or arg1 == '--help':
            print('feature not implemented yet')
            # TODO - add instructions here
        elif arg1 == 'd' or arg1 == 'del':
            print('feature not implemented yet')

            # TODO add option to delete from list here
        else:
            print(f'<{arg1}> is not a valid argument')

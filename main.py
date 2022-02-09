import ntpath
import os

from bs4 import BeautifulSoup as bs
import requests
import logging
from os import path
from pathlib import Path



logging.basicConfig(filename='test.log', level=logging.DEBUG)



# TODO - add logging of errors
#     -create lof of each attempt

def get_podcast_details(rss_url):
    """

    :param rss_url:
    :return:
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
        podcast_details.append((convertedDate + '_' + title + '.mp3', audioUrl))
    return podcast_details


def get_podcasts_to_download(podcast_details, last_update, prev_failed_downloads):
    newList=[]


    for name, url in podcast_details:
        podcast_date = name[0:10]
        print(podcast_date)
        print(name)
        print(url)
        if podcast_date>=last_update:
            newList.append((name,url))
        elif name in prev_failed_downloads:
            newList.append((name,url))

        #add contents of failed log

            #if before date
            #note: all items in list should be in order by date
                #break loop

            #if already in list skip





    return newList




def get_lexicon_valley_podcasts(parent_directory):
    subDirectory = path.join(parent_directory, 'lexValley')
    if not os.path.exists(subDirectory):
        os.makedirs(subDirectory)
    os.chdir(subDirectory)
    print(os.getcwd())




    podcast_details = get_podcast_details()
    podcasts_to_download = get_podcasts_to_download(podcast_details)
    # download_podcasts(podcasts_to_download)


def download_file(url, filename, data_size=10 * 1024 * 1024):
    with requests.get(url, stream=True) as req:
        req.raise_for_status()
        # if error, send to error log

        with open(filename,
                  'wb',
                  ) as new_audio_file:
            for chunk in req.iter_content(chunk_size=data_size):
                new_audio_file.write(chunk)


def get_month_num(month:str)->str:
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


def convert_date_to_YYYYMMDD_date(date_string):
    dateParts = date_string.split()

    new_date_string = dateParts[3] + '-' + get_month_num(dateParts[2]) + '-' + dateParts[1];
    return new_date_string


def get_list_of_podcasts(directory):
    podcasts = []
    podcast_filename = path.join(directory, 'podcastTitles.txt' )
    with open(podcast_filename, 'r') as pc_file:
        for line in pc_file.readlines():
            split = line.split('\t')
            podcast = split[0].strip()
            url = split[1].strip()
            podcasts.append((podcast, url))

    return podcasts


def get_last_update(update_path):
    filename = path.join(update_path, 'update.txt')
    if not path.isfile(filename):
        return None

    with open(filename, 'r') as f:
        lastUpdate = f.readline()

    return lastUpdate

def ensure_dir_exists(dir):

    if not path.isdir(dir):
        Path(dir).mkdir(parents=True)


def attempt_download_all_of_pc(podcast, rss_url, directory):
    pod_cast_dir = path.join(directory,podcast)
    ensure_dir_exists(pod_cast_dir)
    last_update = get_last_update(pod_cast_dir)


    podcast_details = get_podcast_details(rss_url)   #get details from RSS feed
    failed_filename = path.join(directory, 'failed.txt')
    prev_failed_downloads = []

    with open(failed_filename, 'r') as failed_read:
        lines = failed_read.readlines()
        for line in lines:
            prev_failed_downloads.append(line.split('\t')[0].strip())
    podcasts_toDownload = get_podcasts_to_download(podcast_details, last_update,prev_failed_downloads)


    with open(failed_filename, 'w') as failed_write:


        for podcast, url in podcasts_toDownload:
            try:
                download_file(url,podcast)
            except OSError:
                failed_write.write(f'{podcast}\tfailed\f{OSError}\n')
            except Exception as e:
                failed_write.write(f'{podcast}\tfailed\f{type(e).__name__}\n')



    # for p in podcast_details:
    #     print(p)
   # for each download after last update
        #check if downloaded
        #chck if room in file system
        #try download
        #if fail, try again
        #if fail second time - log error
        #if succuss, log sucess

    pass



def run_program():
    directory =  path.join(str(Path.home()),'Downloads/Podcasts')
    podcasts_list = get_list_of_podcasts(directory)
    print(f'dir is: {directory}')
    for podcast, rss_url in podcasts_list:
        attempt_download_all_of_pc(podcast, rss_url, directory)


    #get_lexicon_valley_podcasts(directory)
    # downloadFile(
    #     'https://www.podtrac.com/pts/redirect.mp3/pdst.fm/e/chtbl.com/track/28D492/traffic.megaphone.fm/SLT9922135587.mp3?updated=1624297720',
    #     'temp.mp3')
    # print(convert_date_to_YYYYMMDD_date('Tue, 06 Jul 2021 09:31:29 -0000'))


if __name__ == '__main__':
    run_program()

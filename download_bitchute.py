import argparse
import json

import youtube_dl

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('links_file', type=argparse.FileType('r'))
    args = parser.parse_args()
    links = json.load(args.links_file)

    failed_links = []
    ydl_opts = {"writesubtitles": True, "writeautomaticsub": True, "subtitleslangs": ["en"]}
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        for link in links:
            try:
                ydl.download([link])
            except (youtube_dl.utils.DownloadError, IndexError):
                print(f"Error downloading {link}")
                failed_links.append(link)
    json.dumps(failed_links, open('data/failed_bitchute_links.json', 'w'))
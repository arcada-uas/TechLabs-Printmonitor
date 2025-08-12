from config import config
import asyncio
import requests
import json
from pathlib import Path
import time

def download_json(url, data_path):
    try:
        response = requests.get(url)
        response.raise_for_status()

        response_data = response.json()
        try:
            json_data_file = open(data_path, "r")
            json_data = json.load(json_data_file)
            json_data_file.close()
            if data_path == "static/content/meme_data.json": # This ugly loop is to prevent the "last featured" date from being overwritten
                for response_item in response_data:
                    if response_item["featured"] == "pending":
                        for json_item in json_data:
                            if response_item["filename"] == json_item["filename"]:
                                if json_item["featured"]:
                                    response_item["featured"] = json_item["featured"]
        except(FileNotFoundError):
            print("No previous data on file.")
        json_data_file = open(data_path, "w")
        json.dump(response_data, json_data_file, indent=4)
        json_data_file.close()
        return response_data
    except requests.exceptions.RequestException as e:
        return False

async def download_file(url, target_dir, permitted_extensions):
    filename = url.split('/')[-1]
    extension = filename.split('.')[-1]
    if extension.lower() in permitted_extensions:
        try:
            response = requests.get(url)
            response.raise_for_status()
            with open(f'static/content/{target_dir}{filename}', 'wb') as outfile:
                outfile.write(response.content)
        except requests.exceptions.RequestException as e:
            print(e)
            return False
    else:
        print('DENIED! Only the following file extensions are allowed:', permitted_extensions)


async def download_approved_content(json_data, target_dir, permitted_extensions=['jpg', 'jpeg', 'png', 'gif']):
    for item in json_data:
        if item['approved']:
            filename = item['filename']
            # First, check if the file has been downloaded already!
            filepath = Path("static/content/" + target_dir + filename)
            if filepath.exists():
                print("File exists:", filename)
            else:
                print("Preparing to download file:", config.content_url + "/static/"  + filename, "to", target_dir, "permitted extensions:", permitted_extensions)
                await download_file(config.content_url + "/static/"  + filename, target_dir, permitted_extensions)

def check_for_updates():
    meme_data = download_json(config.content_url + "/api/memes/", "static/content/meme_data.json")
    if meme_data:
        asyncio.run(download_approved_content(meme_data, "images/"))

    job_data = download_json(config.content_url + "/api/jobs/", "static/content/job_data.json")
    if job_data:
        asyncio.run(download_approved_content(job_data, "stl_files/", permitted_extensions=['stl', '3mf']))

if __name__ == "__main__":
    while True:
        check_for_updates()
        time.sleep(59)

import json
import bs4.element
import requests
import time
import progressbar
from collections import defaultdict

from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:60.0) Gecko/20100101 Firefox/60.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
}


def extract_item_data(href: str, info_block: bs4.Tag, name_to_info: dict) -> dict:
    item_url = "https://rustlabs.com" + href

    item_name = str(info_block.find_all(class_="r-cell")[0].getText())

    item_id = name_to_info.get(item_name, {}).get("id", "N/A")
    stack_size = name_to_info.get(item_name, {}).get("stack_size", "N/A")
    despawn_time = name_to_info.get(item_name, {}).get("despawn_time", "N/A")

    appending = {
        "name": info_block.find_all(class_="r-cell")[0].getText(),
        "image": "https:" + info_block.find_all("img")[0]["src"],
        "id": item_id,
        "stack_size": stack_size,
        "despawn_time": despawn_time,
        "crafting_components": [],
        "recycled_components": []
    }

    print(f"Scraping {item_url} for " + appending["name"] + " ID")

    try:
        item = requests.get(item_url, headers=HEADERS)

        if item.status_code != 200:
            return appending

        bs = BeautifulSoup(item.content, "html.parser")
        td = bs.find_all(class_="stats-table")[0].find_all("td")
        td2 = []
        td3 = []
        if bs.find_all(class_="tab-page tab-table", attrs={"data-name": "recycle"}) != []:
            td2 = bs.find_all(class_="tab-page tab-table", attrs={"data-name": "recycle"})[0].find_all("td")
        if bs.find_all(class_="tab-page tab-table", attrs={"data-name": "craft"}) != []:
            td3 = bs.find_all(class_="tab-page tab-table", attrs={"data-name": "craft"})[0].find_all("td")

    except Exception as e:
        print(f"Error occurred while trying to scrape {item_url} for ID. Exception {e}")
        return appending

    if td != [] and len(td) >= 6:
        appending["id"] = td[1].getText()
        appending["stack_size"] = td[3].getText().replace("×", "")
        appending["despawn_time"] = td[5].getText().replace("min ", "mins").replace("hour ", "hour")


    # Check if td2 is not empty and has the required elements
    if td2 != [] and len(td2) > 1:
        # Extract item name
        item_name_tag = td2[1].find('img', class_='')
        item_name = item_name_tag.get('alt') if item_name_tag else "N/A"

        # Extract components with their counts
        components = td2[1].find_all('a', class_='item-box')
        for component in components:
            component_name_tag = component.find('img')
            component_name = component_name_tag.get('alt') if component_name_tag else "N/A"
            component_count_tag = component.find('span', class_='text-in-icon')
            component_count = component_count_tag.text.replace("×", "") if component_count_tag else "N/A"
            appending["recycled_components"].append({"name": component_name, "count": component_count})

    else:
        print("No recycle component information found.")


        # Check if td2 is not empty and has the required elements
    if td3 != [] and len(td3) > 1:
        # Extract item name
        item_name_tag = td3[2].find('img', class_='')
        item_name = item_name_tag.get('alt').replace(" Blueprint", "") if item_name_tag else "N/A"

        # Extract components with their counts
        components = td3[2].find_all('a', class_='item-box')
        for component in components:
            component_name_tag = component.find('img')
            component_name = component_name_tag.get('alt') if component_name_tag else "N/A"
            component_count_tag = component.find('span', class_='text-in-icon')
            component_count = component_count_tag.text.replace("×", "") if component_count_tag else "N/A"
            if component_count == "":
                component_count = "1"
            appending["crafting_components"].append({"name": component_name, "count": component_count})

    else:
        print("No crafting component information found.")

    print("Appending:", appending)

    return appending


def main() -> None:
    print("Starting Rust Labs Scraper")
    response = requests.get('https://rustlabs.com/group=itemlist', headers=HEADERS)

    if response.status_code != 200:
        print("An Error Has Occurred with request")
        quit(1)

    output_json = defaultdict(list)
    output_markdown = "|Name|Image|ID|Stack Size|Despawn Time|Crafting Components|Recycled Components|\n|:-:|:-:|:-:|:-:|:-:|:-:|:-:|\n"

    soup = BeautifulSoup(response.content, 'html.parser')
    info_blocks = soup.find_all('div', class_='info-block group')

    current_heading = ""
    blocks = info_blocks[0].find_all(recursive=False)
    bar = progressbar.ProgressBar(maxval=len(blocks), widgets=[progressbar.Bar('=', '[', ']'), ' ',
                                                               progressbar.Percentage()])
    bar.start()

    name_to_info = {}
    try:
        previousfile = json.load(open("data/items.json", "r"))
        for item_type in previousfile:
            for item in previousfile[item_type]:
                name_to_info[item["name"]] = {"image": item["image"], "id": item["id"],
                                              "stack_size": item["stack_size"], "despawn_time": item["despawn_time"], "crafting_components": item["crafting_components"], "recycled_components": item["recycled_components"]}
    except:
        print("File does not exist or an error occurred.")

    for i, info_block in enumerate(blocks):
        if info_block.name == "h2":
            current_heading = info_block.getText()
        else:
            data = extract_item_data(info_block.get_attribute_list("href")[0], info_block, name_to_info)

            output_json[current_heading].append(data)
            output_markdown += f"|{data['name']}|![]({data['image']})|{data['id']}|{data['stack_size']}|" \
                               f"{data['despawn_time']}|{data['crafting_components']}|{data['recycled_components']}|\n"
            bar.update(i + 1)
            time.sleep(0.5)

    bar.finish()
    name_to_info_output = {}
    for item_type in output_json:
        for item in output_json[item_type]:
            name_to_info_output[item["name"]] = {"image": item["image"], "id": item["id"],
                                                 "stack_size": item["stack_size"], "despawn_time": item["despawn_time"], "crafting_components": item["crafting_components"], "recycled_components": item["recycled_components"]}

    with open("data/items.md", "w") as md_out:
        md_out.write(output_markdown)

    with open("data/items.json", "w") as json_out:
        json_out.write(json.dumps(output_json, indent=3))

    with open("data/name_to_info.json", "w") as name_info_out:
        name_info_out.write(json.dumps(name_to_info_output, indent=3))


if __name__ == '__main__':
    main()

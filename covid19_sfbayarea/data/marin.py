#!/usr/bin/env python3
import csv
from typing import List, Dict, Tuple
from bs4 import BeautifulSoup # type: ignore
from urllib.parse import unquote_plus
from datetime import datetime
from contextlib import contextmanager
 
from ..webdriver import get_firefox
from .utils import get_data_model

def get_county() -> Dict:
    """Main method for populating county data"""

    url = 'https://coronavirus.marinhhs.org/surveillance'
    model = get_data_model()

    chart_ids = {"cases": "Eq6Es", "deaths": "Eq6Es", "tests": '2Hgir', "age": "VOeBm", "gender": "FEciW", "race_eth": "aBeEd"} 
    # population totals and transmission data missing.
    driver = get_firefox()    

    model['name'] = "Marin County"
    model['update_time'] = datetime.today().isoformat()
    model["meta_from_baypd"] = "There's no actual update time on their website. Not all charts are updated daily."
    model['source_url'] = url
    #model['meta_from_source'] = get_metadata(url, chart_ids)
    model['meta_from_source'] = get_chart_meta(url, chart_ids)

    # model["series"]["cases"] = get_case_series(chart_ids["cases"], url) 
    # model["series"]["deaths"] =  get_death_series(chart_ids["deaths"], url)
    # model["series"]["tests"] = get_test_series(chart_ids["tests"], url)
    # model["case_totals"]["age_group"], model["death_totals"]["age_group"] = get_breakdown_age(chart_ids["age"], url)
    # model["case_totals"]["gender"], model["death_totals"]["gender"] = get_breakdown_gender(chart_ids["gender"], url)
    # model["case_totals"]["race_eth"], model["death_totals"]["race_eth"] = get_breakdown_race_eth(chart_ids["race_eth"], url)
    return model

@contextmanager
def chart_frame(driver, chart_id: str):
    frame = driver.find_element_by_css_selector(f'iframe[src*="//datawrapper.dwcdn.net/{chart_id}/"]')
    driver.switch_to.frame(frame)
    try:
        yield frame
    finally:
        driver.switch_to.default_content()

def get_chart_data(url, driver, chart_id: str) -> List[str]:
    """This method extracts parsed csv data from the csv linked in the data wrapper charts."""
    with get_firefox() as driver:
        driver.implicitly_wait(30)
        driver.get(url)

        with chart_frame(driver, chart_id):
            csv_data = driver.find_element_by_class_name('dw-data-link').get_attribute('href')
            # Deal with the data
            if csv_data.startswith('data:'):
                media, data = csv_data[5:].split(',', 1)
                # Will likely always have this kind of data type
                if media != 'application/octet-stream;charset=utf-8':
                    raise ValueError(f'Cannot handle media type "{media}"')
                csv_string = unquote_plus(data)
                csv_data = csv_string.splitlines()
            else:
                raise ValueError('Cannot handle this csv_data href')

    return csv_data

def get_chart_meta(url, chart_ids: Dict[str, str]) -> List:
    """This method gets all the metadata underneath the data wrapper charts and the metadata."""
    with get_firefox() as driver: 
        driver.implicitly_wait(30)
        driver.get(url)
        soup = BeautifulSoup(driver.page_source, 'html5lib')
        metadata = set()
        
        chart_metadata = set()

        for soup_obj in soup.findAll('div', attrs={"class":"surveillance-data-text"}):
            if soup_obj.findAll('p'):
                metadata = set({paragraph.text.replace("\u2014","").replace("\u00a0", "").replace("\u2019","") for paragraph in soup_obj.findAll('p')})
            else:
                raise ValueError('Metadata location has changed.')

        # Metadata for each chart visualizing the data of the csv file I'll pull.
        
        # new function 
        for chart_id in chart_ids.values():
            with chart_frame(driver, chart_id):
                for soup_obj in soup.findAll('div', attrs={"class": 'notes-block'}):
                    #chart_metadata = soup_obj
                    if soup_obj.findAll('span'):
                        chart_metadata = set({obj.text for obj in soup_obj.findAll('span')})
                    else:
                        raise ValueError('Metadata location has changed.')

            # Switch back to the parent frame to "reset" the context
            #driver.switch_to.parent_frame() # I think this is handled by the context manager

        # old function - to be deleted
        # for chart_id in chart_ids.values():
        #     with chart_frame(driver, chart_id):
        #         notes = driver.find_elements_by_class_name('dw-chart-notes')
        #         chart_metadata = list({note.text for note in notes})

    # Return the metadata. I take the set of the chart_metadata since there are repeating metadata strings.
    return list(metadata), list(chart_metadata)

def extract_csvs(chart_id: str, url: str) -> str:
    """This method extracts the csv string from the data wrapper charts."""
    driver = get_firefox()    
    driver.implicitly_wait(30)
    driver.get(url)

    frame = driver.find_element_by_css_selector(f'iframe[src*="//datawrapper.dwcdn.net/{chart_id}/"]')

    driver.switch_to.frame(frame)
    # Grab the raw data out of the link's href attribute
    csv_data = driver.find_element_by_class_name('dw-data-link').get_attribute('href')

    # Deal with the data
    if csv_data.startswith('data:'):
        media, data = csv_data[5:].split(',', 1)
        # Will likely always have this kind of data type
        if media != 'application/octet-stream;charset=utf-8':
            raise ValueError(f'Cannot handle media type "{media}"')
        csv_string = unquote_plus(data)
    else:
        raise ValueError('Cannot handle this csv_data href')

    # Then leave the iframe
    driver.switch_to.default_content()

    return csv_string

def get_metadata(url: str, chart_ids: Dict[str, str]) -> Tuple[List, List]:

    # Metadata for each chart visualizing the data of the csv file I'll pull. 
    for chart_id in chart_ids.values():
        frame = driver.find_element_by_css_selector(f'iframe[src*="//datawrapper.dwcdn.net/{chart_id}/"]')
        driver.switch_to.frame(frame)
        # The metadata for the charts is located in elements with the class `dw-chart-notes' 
        for c in driver.find_elements_by_class_name('dw-chart-notes'):
            chart_metadata.add(c.text)

        # Switch back to the parent frame to "reset" the context
        driver.switch_to.parent_frame()

    driver.quit() 

    # Return the metadata. I take the set of the chart_metadata since there are repeating metadata strings.
    return metadata, list(chart_metadata)

def get_case_series(chart_id: str, url: str, driver) -> List:
    """This method extracts the date, number of cumulative cases, and new cases."""
    
    csv_data = get_chart_data(url, driver, chart_id)
    csv_reader = csv.DictReader(csv_data)
    # csv_str = extract_csvs(chart_id, url)
    # csv_reader = csv.DictReader(csv_str.splitlines())

    keys = csv_reader.fieldnames

    series: list = list()

    if keys != ['Date', 'Total Cases', 'Total Recovered*', 'Total Hospitalized', 'Total Deaths']:
        raise ValueError('The headers have changed')

    case_history = []

    for row in csv_reader:
        daily: dict = dict()
        date_time_obj = datetime.strptime(row['Date'], '%m/%d/%Y')
        daily["date"] = date_time_obj.strftime('%Y-%m-%d')
        # Collect the case totals in order to compute the change in cases per day 
        case_history.append(int(row["Total Cases"]))
        daily["cumul_cases"] = int(row["Total Cases"]) 
        series.append(daily)

    case_history_diff = []
    # Since i'm substracting pairwise elements, I need to adjust the range so I don't get an off by one error.
    for i in range(0, len(case_history)-1):
        case_history_diff.append((int(case_history[i+1]) - int(case_history[i])) + int(series[0]["cumul_cases"]))
        # from what I've seen, series[0]["cumul_cases"] will be 0, but I shouldn't assume that.
    case_history_diff.insert(0, int(series[0]["cumul_cases"]))

    for val, case_num in enumerate(case_history_diff):
        series[val]["cases"] = case_num 
    return series

def get_death_series(chart_id: str, url: str, driver) -> List:
    """This method extracts the date, number of cumulative deaths, and new deaths."""
    csv_data = get_chart_data(url, driver, chart_id)
    csv_reader = csv.DictReader(csv_data)
    # csv_str = extract_csvs(chart_id, url)
    # csv_reader = csv.DictReader(csv_str.splitlines())
    keys = csv_reader.fieldnames

    series: list = list()

    if keys != ['Date', 'Total Cases', 'Total Recovered*', 'Total Hospitalized', 'Total Deaths']:
        raise ValueError('The headers have changed.')

    death_history = []

    for row in csv_reader:
        daily: dict = dict()
        date_time_obj = datetime.strptime(row['Date'], '%m/%d/%Y')
        daily["date"] = date_time_obj.strftime('%Y-%m-%d')
        # Collect the case totals in order to compute the change in cases per day 
        death_history.append(int(row["Total Deaths"]))
        daily["cumul_deaths"] = int(row["Total Deaths"])
        series.append(daily)

    death_history_diff = []
    # Since I'm substracting pairwise elements, I need to adjust the range so I don't get an off by one error.
    for i in range(0, len(death_history)-1):
        death_history_diff.append((int(death_history[i+1]) - int(death_history[i])) + int(series[0]["cumul_deaths"]))
        # from what I've seen, series[0]["cumul_cases"] will be 0, but I shouldn't assume that.
    death_history_diff.insert(0, int(series[0]["cumul_deaths"]))

    for val, case_num in enumerate(death_history_diff):
        series[val]["deaths"] = case_num
    return series

def get_breakdown_age(chart_id: str, url: str, driver) -> Tuple[List, List]:
    """This method gets the breakdown of cases and deaths by age."""
    csv_data = get_chart_data(url, driver, chart_id)
    csv_reader = csv.DictReader(csv_data)
    # csv_str = extract_csvs(chart_id, url)
    # csv_reader = csv.DictReader(csv_str.splitlines())
    keys = csv_reader.fieldnames

    c_brkdown: list = list()
    d_brkdown: list = list()

    if keys != ['Age Category', 'POPULATION', 'Cases', 'Hospitalizations', 'Deaths']:
        raise ValueError('The headers have changed')

    key_mapping = {"0-18": "0_to_18", "19-34": "19_to_34", "35-49": "35_to_49", "50-64": "50_to_64", "65-79": "65_to_79", "80-94": "80_to_94", "95+": "95_and_older"} 

    for row in csv_reader:
        c_age: dict = dict()
        d_age: dict = dict()
         # Extracting the age group and the raw count for both cases and deaths.
        c_age["group"], d_age["group"] = row['Age Category'], row['Age Category']
        if c_age["group"] not in key_mapping:
            raise ValueError(str(c_age["group"]) + ' is not in the list of age groups. The age groups have changed.')
        else:
            c_age["group"] = key_mapping[c_age["group"]]
            c_age["raw_count"] = int(row["Cases"])
            d_age["group"] = key_mapping[d_age["group"]]
            d_age["raw_count"] = int(row["Deaths"])
            c_brkdown.append(c_age)
            d_brkdown.append(d_age)

    return c_brkdown, d_brkdown

def get_breakdown_gender(chart_id: str, url: str, driver) -> Tuple[Dict, Dict]:
    """This method gets the breakdown of cases and deaths by gender."""
    csv_data = get_chart_data(url, driver, chart_id)
    csv_reader = csv.DictReader(csv_data)
    # csv_str = extract_csvs(chart_id, url)
    # csv_reader = csv.DictReader(csv_str.splitlines())
    keys = csv_reader.fieldnames

    if keys != ['Gender', 'POPULATION', 'Cases', 'Hospitalizations', 'Deaths']:
        raise ValueError('The headers have changed.')

    genders = ['male', 'female']
    c_gender = {}
    d_gender = {}
    
    for row in csv_reader:
        # Extracting the gender and the raw count (the 3rd and 5th columns, respectively) for both cases and deaths.
        # Each new row has data for a different gender.
        gender = row["Gender"].lower()
        if gender not in genders:
            return ValueError("The genders have changed.") # type: ignore 
            # is doing this bad practice? mypy doesn't have an issue with the error on line 244 so not sure why this one causes an error
        c_gender[gender] = int(row["Cases"])
        d_gender[gender] = int(row["Deaths"])            

    return c_gender, d_gender

def get_breakdown_race_eth(chart_id: str, url: str, driver) -> Tuple[Dict, Dict]:
    """This method gets the breakdown of cases and deaths by race/ethnicity."""

    csv_data = get_chart_data(url, driver, chart_id)
    csv_reader = csv.DictReader(csv_data)
    #csv_str = extract_csvs(chart_id, url)
    #csv_reader = csv.DictReader(csv_str.splitlines())
    keys = csv_reader.fieldnames
    
    if keys != ['Race/Ethnicity', 'COUNTY POPULATION', 'Cases', 'Case Percent', 'Hospitalizations', 'Hospitalizations Percent', 'Deaths', 'Deaths Percent']:
        raise ValueError("The headers have changed.")

    key_mapping = {"black/african american":"African_Amer", "hispanic/latino": "Latinx_or_Hispanic",
            "american indian/alaska native": "Native_Amer", "native hawaiian/pacific islander": "Pacific_Islander", "white": "White", "asian": "Asian", "multi or other race": "Multi or Other Race"}
            # "Multiple_Race", "Other" are not separate in this data set - they are one value under "Multi or Other Race"

    c_race_eth = {}
    d_race_eth = {}

    for row in csv_reader:
        race_eth = row["Race/Ethnicity"].lower()
        if race_eth not in key_mapping:
            raise ValueError("The race_eth groups have changed.")
        else:
            c_race_eth[key_mapping[race_eth]] = int(row["Cases"])
            d_race_eth[key_mapping[race_eth]] = int(row["Deaths"])

    return c_race_eth, d_race_eth

def get_test_series(chart_id: str, url: str) -> List:
    """This method gets the date, the number of positive and negative tests on that date, and the number of cumulative positive and negative tests."""
    csv_data = get_chart_data(url, driver, chart_id)
    # csv_ = extract_csvs(chart_id, url)
    # csv_strs = csv_.splitlines()

    dates, positives, negatives = [row.split(',')[1:] for row in csv_data] 
    series = zip(dates, positives, negatives)

    test_series: list = list()

    cumul_pos = 0
    cumul_neg = 0
    for entry in series:
        daily: dict = dict()
        # I'm not sure why, but I just found out that some of the test series have a 'null' value (in the spot where the number of positive tests is), so I needed to account for that here.
        # At least for now, it's only present at the end, so I just break out of the loop and return the test series. 
        if entry[1] != 'null':
            date_time_obj = datetime.strptime(entry[0], '%m/%d/%Y')
            daily["date"] = date_time_obj.strftime('%Y-%m-%d')
            daily["positive"] = int(entry[1])
            cumul_pos += daily["positive"]
            daily["negative"] = int(entry[2])
            cumul_neg += daily["negative"]
            daily["cumul_pos"] = cumul_pos
            daily["cumul_neg"] = cumul_neg
            test_series.append(daily)
        else:
            break
        
    return test_series

get_county()

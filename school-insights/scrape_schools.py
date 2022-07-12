import requests as reqs
from bs4 import BeautifulSoup as bs
import re
import json
import fitz

from fake_useragent import UserAgent
ua = UserAgent()
ua_header = {'User-Agent': str(ua.chrome)}

def get_top_lvl_tables(soup, array_idx): # Works
    """
    This function takes raw soup as an input gets top level tables for each top level category such as primary schools,
    secondary school, teacher finances and so on. It returns a dictionary containing the top level name
    and the link to that top level name (to be used with the base link). # {'high_lvl_cat: ['links]'}
    """
    ordered_list_lis = soup.select('ol.govuk-tabs__list')[0].find_all('li')
    data_sv = dict()
    # reason_sv = dict()
    if len(array_idx) == 2:
        for l in ordered_list_lis[array_idx[0]: array_idx[1]]:
            l_link = l.find('a')['href']
            l_upper = l.find('a').contents[2]
            l_lower = l.find('a').contents[4]
            l_lower = re.sub(r"[^\w\s]", '', l_lower) # For lower
            l_lower = re.sub(r"\s+", '_', l_lower)
            l_upper = re.sub(r"[^\w\s]", '', l_upper) # For upper
            l_upper = re.sub(r"\s+", '_', l_upper)
            l_full = f'{l_upper.upper()}_{l_lower.upper()}'
            data_sv[f'{l_full[1:]}'] = {'link': l_link}
    else:
        l = ordered_list_lis[array_idx[0]]
        l_link = l.find('a')['href']
        l_upper = l.find('a').contents[2]
        l_lower = l.find('a').contents[4]
        l_lower = re.sub(r"[^\w\s]", '', l_lower) # For lower
        l_lower = re.sub(r"\s+", '_', l_lower)
        l_upper = re.sub(r"[^\w\s]", '', l_upper) # For upper
        l_upper = re.sub(r"\s+", '_', l_upper)
        l_full = f'{l_upper.upper()}_{l_lower.upper()}'
        data_sv[f'{l_full[1:]}'] = {'link': l_link}
    return data_sv

def get_tables_each_top(data_sv, get_table_all_pages, find_col_heads, find_table_data, array_idx): # Works
    """
    Function finds all the table content across all pages for a particular parent category.
    It assumes these parent categories are already known and goes throught the supplied dictionary.
    Function returns error if unfamiliar table structure gets encountered and returns the saved
    dictionary if all is good. Will make into class if have time
    """
    if len(array_idx) == 2 or len(array_idx) == 1:
        try:
            if len(array_idx) == 2:
                for col_name in list(data_sv.keys())[array_idx[0]: array_idx[1]]:
                    try:
                        base_url = 'https://www.compare-school-performance.service.gov.uk'
                        add_url = data_sv[col_name]['link']
                        page_selector = '&page='
                        # Saves the unique table identifiers and table data for each table
                        data_sv[col_name], data_sv[col_name]['reason_sv'] = get_table_all_pages(base_url, add_url, page_selector, find_col_heads, find_table_data)
                        # print(f"reason_sv in main data_sv: {data_sv[col_name]['reason_sv']}")
                    except Exception as e:
                        e  = e
                        print(f"Not same table structure, Reason: {e}")
            elif len(array_idx) == 1:
                col_name = list(data_sv.keys())[array_idx[0]]
                try:
                    base_url = 'https://www.compare-school-performance.service.gov.uk'
                    add_url = data_sv[col_name]['link']
                    page_selector = '&page='
                    # Saves the unique table identifiers and table data for each table
                    data_sv[col_name], data_sv[col_name]['reason_sv'] = get_table_all_pages(base_url, add_url, page_selector, find_col_heads, find_table_data)
                    # print(f"reason_sv in main data_sv: {data_sv[col_name]['reason_sv']}")
                except Exception as e:
                    e  = e
                    print(f"Not same table structure, Reason: {e}")                
            return data_sv
        except Exception as e:
            print(f"This is likely an index error, Reason: {e}")
            pass
    else:
        raise Exception(f"Only array_idx of len == (2 or 1) are allowed.")

def get_table_all_pages(base_url, top_lvl_url, page_selector, find_col_names, find_table_data): # Works
    def next_page_exists(soup, page):
        """
        This function returns true if the final paginator, within a single pagination unordered
        list, has 'Next' in its contents (if a next button exists). If there's no next button, the end
        of the table has been reached and True is returned.
        """
        paginators = soup.find_all('ul', attrs = {'class': 'pagination'})[0]
        next_page = paginators.find_all('a')[-1].contents[0] # Checks if last li in ul has next 
        if next_page == 'Next':
            print(f'Current Page: {page}, Moving onto the Next Page')
            return True
        print(f'Current Page: {page}, Last Page Reached!\n\n')
        return False

    try:
        pages = 0
        next_page = True
        found_col_names = False
        urls = []
        reason_sv = {}
        while next_page:
            pages += 1
            full_url = base_url + top_lvl_url + page_selector + str(pages)
            urls.append(full_url)
            html_raw = reqs.get(full_url, headers = ua_header)
            soup = bs(html_raw.content)
            # Checking to see if colnames have already been found
            if not found_col_names:
                data_sv = find_col_names(soup)
                data_sv, reason_sv = find_table_data(data_sv, reason_sv, soup)
                found_col_names = True
            else:
                data_sv, reason_sv = find_table_data(data_sv, reason_sv, soup)
            next_page = next_page_exists(soup, pages)
        return data_sv, reason_sv
    except Exception as e:
        print(f"Exception Encountered, Reason: {e}\n\
                Returning data_sv and reason_sv so far:")
        return data_sv, reason_sv
        ####


# Header depends on what the type of data being gotten is
def find_col_heads(soup): # Works
    """
    This function finds the table head names and some of their attribute vales and saves them to a Python
    dictionary. It assumes each table head is organised into table rows and that when the colspan of a table
    head item is not 1, it refers to the next few items of the second table row (the number of items chosen
    depends on the colspan in the previous table row).
    """
    header_and_table = soup.find_all('div', attrs={'id': 'table-sticky-header-container'})
    header_and_table = header_and_table[0].find('table', attrs={'id': 'establishment-list-view'})
    header = header_and_table.find('thead') # First thead contains the table headers
    header_trs = header.find_all('tr')

    if len(header_trs) == 4: # For table col heads with 2 lvls
        upper_theads = header_trs[-2].find_all('th') 
        lower_theads = header_trs[-1].find_all('th') 
    elif 2 <= len(header_trs) <= 3: # For table col heads with 1 lvl
        upper_theads = header_trs[-1].find_all('th')
    else:
        raise ValueError("Expected either 3 or 4 header rows")
    
    # Init Values
    count = 0
    data_sv = {} # {'upper_word': {'col_items': col_items, 'pdf_data': [], 'col_class': col_class}}
    
    # For loop
    for th in upper_theads:
        try:
            upper_word = th.find('a').contents[0].strip()
        except Exception as e:
            upper_word = th.contents[0].strip()
        col_span = int(th['colspan'])
        col_idx = int(th['data-column-index'])
        col_class = th['class'][0]
        if col_span == 1:
            upper_word = re.sub(r"[^\w\s]", '', upper_word)
            upper_word = re.sub(r"\s+", '_', upper_word)
            # Init with empty array to leave space for values
            data_sv[f'{upper_word.upper()}'] = {'col_items': [], 'col_datatype': col_class, 'pdf_reports':\
                    {'link': [], 'content': {'text': [], 'img_data': []}, 'inspection_type': [], 'inspection_outcome': [],\
                    'published_date': [], 'inspection_date': []}}
            print(f"upper_word: {upper_word}, col_idx: {col_idx}, count: {count}, col_span: {col_span}, col_class: {col_class}\n\n" )
        else:  
            # This saves the previous count and uses it in while loop
            if count == 0:
                while count != col_span:
                    lower_word = lower_theads[count].find('a').contents[0].strip()
                    col_span_l = int(lower_theads[count]['colspan'])
                    col_idx_l = int(lower_theads[count]['data-column-index'])
                    col_class_l = lower_theads[count]['class'][0]
                    # Init with empty array to leave space for values
                    lower_word = re.sub(r"[^\w\s]", '', lower_word)
                    lower_word = re.sub(r"\s+", '_', lower_word)
                    data_sv[f'{lower_word.upper()}'] = {'col_items': [], 'col_datatype': col_class_l, 'pdf_reports':\
                    {'link': [], 'content': {'text': [], 'img_data': []}, 'inspection_type': [], 'inspection_outcome': [],\
                    'published_date': [], 'inspection_date': []}}

                    # Update Count
                    count += 1

                    # Checking Values
                    print(f"upper_word: {lower_word}, col_idx_l: {col_idx_l}, count: {count}, col_span: {col_span_l}, col_class: {col_class_l}\n\n" )
                # Save Previous Count
                previous_count = count
            elif count > 0:
                while count != (col_span + previous_count):
                    lower_word = lower_theads[count].find('a').contents[0].strip()
                    col_span_l = int(lower_theads[count]['colspan'])
                    col_idx_l = int(lower_theads[count]['data-column-index'])
                    col_class_l = lower_theads[count]['class'][0]
                    # Init with empty array to leave space for values
                    lower_word = re.sub(r"[^\w\s]", '', lower_word)
                    lower_word = re.sub(r"\s+", '_', lower_word)
                    data_sv[f'{lower_word.upper()}'] = {'col_items': [], 'col_datatype': col_class_l, 'pdf_reports': \
                    {'link': [], 'content': {'text': [], 'img_data': []}, 'inspection_type': [], 'inspection_outcome': [],\
                    'published_date': [], 'inspection_date': []}}

                    # Update Count
                    count += 1

                    # Checking Values
                    print(f"upper_word: {lower_word}, col_idx_l: {col_idx_l}, count: {count}, col_span: {col_span_l}, col_class: {col_class_l}\n\n" )
                # Save Previous Count
                previous_count = count
    return data_sv

def find_table_data(data_sv, reason_sv, soup): # Works
    # Using soup to find body
    header_and_table = soup.find_all('div', attrs={'id': 'table-sticky-header-container'})
    header_and_table = header_and_table[0].find('table', attrs={'id': 'establishment-list-view'})
    body = header_and_table.find('tbody') # First tbody contains the table body
    body_trs = body.find_all('tr', attrs = {'data-row-id': 'SchoolsResultsRow'})

    row_idx = 0
    for row_data in body_trs:
        data_sv, reason_sv = find_row_data(data_sv, reason_sv, row_data, row_idx) 
        row_idx += 1
    return data_sv, reason_sv

def find_row_data(data_sv, reason_sv, row_data, row_idx):
    # Making Functions to see what type of cols exist for suppressing data
    def is_first_row(col):
        if col.name == 'th': # Negates the first column for now
            k = col.find('a').contents[0].strip()
            return True, k
        return False, 'Place_Holder1'

    def is_report_link(col):
        # Fucntion to find latest full inspection date
        def find_full(ofstd_tmln):
            """
            Finds the latest full inspection given we've already found the ol for the page
            containing the ofsted timeline of inspections
            """
            all_lis = ofstd_tmln.find_all('li', attrs={'class': 'timeline__day'})
            # Collecting the lis that have 'full inspection' text
            full_inspections = []
            for lis in all_lis:
                values = lis.find('div', attrs={'class': 'event'})
                a_tag = values.find('a')
                if a_tag is None:
                    pass
                else:
                    inspection_type = a_tag.contents[0].strip()
                    t = 'Full inspection'
                    if t in inspection_type:
                        full_inspections.append(lis)
                    else:
                        pass
            # First value in the list will be the latest full inspection
            return full_inspections[0] if len(full_inspections) >= 1 else []

        # Function to get the ofsted pdf file and download its text and image data
        def get_pdf_data(report_link_pdf):
            """
            USING PYMUPDF --- REFERENCE THIS WHEN TRYNIG TO SHOW DATA IN JUPYTER!!!
            This function uses pymupdf to get text from the ofsted pdf files using OCR
            as well as extracting image objects for each page. These are not image data,
            but its just the object/location of the image in memory.
            """
            res = reqs.get(report_link_pdf, headers = ua_header)
            doc = fitz.open(stream=res.content, filetype="pdf")

            pages = 0
            page_text_data = [] # Per page
            page_pix_data = [] # New object per page
            next_page = True
            while next_page:
                try: # USING PYMUPDF --- REFERENCE THIS WHEN TRYNIG TO SHOW DATA IN JUPYTER
                    page_data = doc.load_page(pages)
                    page_pix_data.append(page_data.get_pixmap())
                    page_text_data.append(page_data.get_text('text'))
                    # Update pages
                    pages += 1
                except Exception as e:
                    next_page = False
                    e = e
                    # print(f"Last PDF Page Reached!, Reason: {e}")
            return page_text_data, page_pix_data

        # These check if the col has an a tag
        if col.name == 'th': # Negates the first column for now
            return False, 'Place_Holder1'
        else:
            k = col["headers"] # Negates help text and is always first header value
            unrolled_headers = "".join(str(val) + " " for val in k)
            if k is None:
                return False, 'Place_Holder1'
            else:
                if 'Link to report' in unrolled_headers:
                    ofsted_link = col.find('a')['href']
                    # Do after finding ofsted page link
                    ofsted_html_raw = reqs.get(ofsted_link, headers =ua_header)
                    ofsted_page_soup = bs(ofsted_html_raw.content)

                    # Getting Ofsted document and page details
                    # Init Vals   
                    ofsted_timelines = ofsted_page_soup.find('ol', attrs={'class': 'timeline'})
                    full_inspections = find_full(ofsted_timelines)
                    # I'm using arrays to save vals incase I want to get multiple vals in future
                    placeholder = None
                    save_inspect = {'link': placeholder, 'content': {'text': placeholder, 'img_data': placeholder},\
                    'inspection_type': placeholder, 'inspection_outcome': placeholder, 'published_date': placeholder, 'inspection_date': placeholder}

                    if len(full_inspections) == 0:
                        inspection_date = 'None'
                        published_date = 'None'
                        report_link_pdf = 'None'
                        inspection_type = 'None'
                        inspection_outcome = 'None'
                    else:
                        latest = full_inspections
                        values = latest.find('div', attrs={'class': 'event'})
                        link_values = values.find('span', attrs={'class': 'event__title'})

                        inspection_date = values.find('p', attrs={'class': 'timeline__date'}).select('time')[0].contents[0]
                        published_date = link_values.find('a').contents[-1].contents[0].split("-")[1].strip() # Always last value of contents
                        
                        report_link_pdf = link_values.find('a')['href']
                        inspection_type = link_values.find('a').contents[0].strip()[:-1] if ":" in\
                                        link_values.find('a').contents[0].strip() else link_values.find('a').contents[0].strip()
                        inspection_outcome = latest.find('a').contents[1].contents[0].strip()
                    # Saving to dictionary
                    save_inspect['link'] = report_link_pdf
                    # PyMuPDF is too slow for now, take advice at end of code!
                    # save_inspect['content']['text'] = get_pdf_data(report_link_pdf)[0] if (len(full_inspections) != 0) else 'None'
                    # save_inspect['content']['img_data'] = get_pdf_data(report_link_pdf)[1] if (len(full_inspections) != 0) else 'None'
                    save_inspect['inspection_type'] = inspection_type
                    save_inspect['inspection_outcome'] = inspection_outcome
                    save_inspect['published_date'] = published_date
                    save_inspect['inspection_date'] = inspection_date
                    return True, save_inspect
                else:
                    return False, 'Place_Holder1'

    def has_replace_tag(col): # Works
        # These check if the col has an a tag
        if col.name == 'th': # Negates the first column for now
            return False, 'Place_Holder1', 'Place_Holder2'
        else:
            k = col.find('span', attrs = {'class': 'value'}) # Negates help text
            if k is None:
                return False, 'Place_Holder1', 'Place_Holder2'
            else:
                try:
                    reason_text = k.find('a')['data-modal-text'].strip()
                    k = k.find('a')['data-modal-title'].strip() # Always first element
                    return True, str(k), str(reason_text)
                except Exception as e:
                    return False, 'Place_Holder1', 'Place_Holder2'
    def is_no_data_row(col): # Works
        if str(col['class']) == 'no-data-row':
            return True
        return False 
    def has_bubble_avg(col): # Works
        try:
            k = col.find('span', attrs = {'class': 'bubble'}).contents
            bubble_text = k[1].contents[0].strip()
            bubble_num = k[3].contents[0].strip()
            bubble_text_and_num = (bubble_text, bubble_num) # Tuple
            val = bubble_text_and_num
            return True, val
        except Exception as e:
            k = 'Place_Holder'
            return False, k
    def is_just_text_col(col): # Works
        try:
            k = col.find('span', attrs = {'class': 'value'}).contents[0].strip()
            return True, k
        except Exception as e:
            k = 'Place_Holder'
            return False, k
    def is_mobile_group_start(col): # Works
        try:
            k = col['class'][0]
            if str(k) == 'mobile-group-start':
                return True
            return False
        except Exception as e:
            return False

    # Initialisting Row Data
    row_data = row_data.find_all(['th', 'td'])
    no_data_remaining_cols = False
    row_data = [td for td in row_data if not is_mobile_group_start(td)]

    for col, col_name in zip(row_data, list(data_sv)):
        if is_first_row(col)[0]:
            _, val = is_first_row(col)
            # print("First column detected: $$$")
        elif has_replace_tag(col)[0]:
            _, val, text = has_replace_tag(col)
            # print(f"has_replace_tag: {val}")
            if val in list(reason_sv):
                # Don't save duplicate entries
                reason_sv[val]['times_seen'] += 1
                # print(f'\ncat_already_seen: {val}, explanation: {text}\n')
            else:
                reason_sv[val] = {'times_seen': 1, 'explanation': text}
                print(f'\nnew_cat_seen: {val}\n')
        elif is_no_data_row(col):
            val = None
            # print("No Data Col detected")
            no_data_remaining_cols = True
        elif no_data_remaining_cols:
            val = None
            # print("No Data Col detected")
        elif is_just_text_col(col)[0]:
            _, val = is_just_text_col(col)
            # print("Text column detected")
        elif has_bubble_avg(col)[0]:
            _, val = has_bubble_avg(col)
            # print("Bubble Col detected")
        elif is_report_link(col)[0]:
            _, save_inspect = is_report_link(col)
            """print(f"\n\nLink to PDF: {save_inspect['link']}, Inspection Type: {save_inspect['inspection_type']},\n\
            Inspection Outcome: {save_inspect['inspection_outcome']}, Inspection Publish Date: {save_inspect['published_date']}\n\
            Actual Inspection Date: {save_inspect['inspection_date']}\n\n")"""
            # Saving to dictionary
            # data_sv[col_name]['pdf_reports']['content']['text'].append(save_inspect['content']['text'])
            # data_sv[col_name]['pdf_reports']['content']['img_data'].append(save_inspect['content']['img_data'])
            data_sv[col_name]['pdf_reports']['link'].append(save_inspect['link'])
            data_sv[col_name]['pdf_reports']['inspection_type'].append(save_inspect['inspection_type'])
            data_sv[col_name]['pdf_reports']['inspection_outcome'].append(save_inspect['inspection_outcome'])
            data_sv[col_name]['pdf_reports']['published_date'].append(save_inspect['published_date'])
            data_sv[col_name]['pdf_reports']['inspection_date'].append(save_inspect['inspection_date'])

        # Appending data to the dictionary for one column
        data_sv[col_name]['col_items'].append(val)
    return data_sv, reason_sv

# Init Values
def get_top_idx(args = [0], max=False):
    if isinstance(args, list):
        if not max:
            if len(args) == 2:
                return [args[0], args[1]]
            else:
                return [args[0]]
        else:
            return [0, 5]
    else:
        raise Exception(f"Inputted arguments are not in list format!")

# Getting Initial Soup
def get_ini_soup():
    base_url = 'https://www.compare-school-performance.service.gov.uk'
    plchldr = '/schools-by-type?for=primary&step=default&table=schools&region=all-england'
    paginator = '&page=1'
    full_url = base_url + plchldr + paginator
    html_raw = reqs.get(full_url, headers = ua_header)
    soup = bs(html_raw.content)
    return soup

if __name__ == '__main__':      
    soup = get_ini_soup()
    array_idx = get_top_idx(max=True) # Workforce
    file_name = 'school_gov_data_8.json'

    # Getting Table Data
    if len(array_idx) == 2:
        for num in range(array_idx[0], array_idx[1]):
            data_sv = get_top_lvl_tables(soup, [num])
            col_name = list(data_sv.keys())[0]
            data_sv = get_tables_each_top(data_sv, get_table_all_pages,\
                        find_col_heads, find_table_data, [0]) # Idx always 0
    if len(array_idx) == 1:
        data_sv = get_top_lvl_tables(soup, array_idx)
        col_name = list(data_sv.keys())[0]
        data_sv = get_tables_each_top(data_sv, get_table_all_pages,\
                    find_col_heads, find_table_data, [0]) # Idx always 0

    with open(file_name, 'w') as j_obj:
        json.dump(data_sv, j_obj, sort_keys = True)
            
"""
Need to create another script to accurately convert all the scraped
information to a either a pandas file/table or with data sorted by list.
I also need another script to save all this data into MONGODB as its already in 
json format (although will be converting the information to sql tables just for the
practice with big data [there are over 100k rows in this dataset!!!]).

I will also optimise this code, although it takes a long series of actions (especially
getting images and text from the pdf ofsted files), it takes around 20-30 minutes to get
all 100k-ish items of data (this is too long) - as well as the console running out of memory
from time to time; I think this is being caused by using PYMuPDF on such large amounts of data
(which is also not very good!). I've tried my best to reduce the time and space complexity in
my code by using dictionaries and resetting them at runtimes (so I don't have to call the
ENTIRE 100k-ish main dictionary to save or search for an item of data).

The next time I scrape such a large amount of data I will be converting all of the above code into
lightweight and sexy class! Although doin this by functions worked, code is not very readable or
re-useable as there are no defined methods or operations (I made up functions as I went along).

Code kept on crashing due to pymupdf so used google colab to execute code instead!!! Code also 
kept crashing on colab (although it got further!), so I will need to use either multithreading or
multiprocessing libraries OR collect all the links to the pdfs and process their information in 
bulk on a GPU (using pooling). So for now, pdf data has been omitted o it can be calculated in future.
"""

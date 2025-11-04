from bs4 import BeautifulSoup, NavigableString, Tag
import re

def reformat_html(html_content):
    soup=BeautifulSoup(html_content, 'html.parser')
    unwanted_words=['CC @Mike.srajer@formlabs.com',"Overview",'[a]','[b]','[c]','_Assigned to _'] #add the unneeded texts here
    soup=remove_comment_links(soup)
    soup=remove_first_table_and_keep_content(soup)
    soup=transform_text_to_warning_div(soup)
    soup=h2_anchor(soup)
    soup=convert_tool(soup)
    soup=convert_li_to_warning_div(soup)
    soup=convert_note_to_tip_div(soup)
    soup=convert_lists_to_steps(soup)
    soup=convert_step_p_to_h3(soup)

    soup=update_alt_text(soup)
    soup=separate_img(soup)
    soup=remove_unnecessary_text(soup,unwanted_words)

    return str(soup.prettify())

def h2_anchor(soup):
    for h1 in soup.find_all('h1'):
        text=h1.get_text(strip=True)
        if not text:
            h1.decompose()
            continue
        #convert spaces to deshes
        anchor_name_dashes = re.sub(r'\s+', '-', text)
        final_anchor_name = anchor_name_dashes.lower()

        #remove the #
        cleaned_text=re.sub(r'^\s*\d+[:.\-)\s]*','',text).strip()
            
        #make new h2 tag
        new_h2 = soup.new_tag("h2", **{'class': 'kb-anchor'})
        new_h2.string = cleaned_text
    
        #create new a tag and passes the name attribute value
        new_anchor = soup.new_tag("a", attrs={'name': final_anchor_name, 'class': 'kb-anchor'})
            
        h1.insert_before(new_anchor)
        h1.insert_before(new_h2)

        h1.decompose()
    return soup


def transform_text_to_warning_div(soup):
    """takes warning div out of the numbered list"""
    for h2 in soup.find_all('h2'):
        text = h2.get_text(strip=True)
        if not text:
            continue

        if re.match(r'^(NOTICE|DANGER|CAUTION|WARNING)\b', text, re.IGNORECASE):
            heading_text = text.capitalize() + ':'

            next_p = h2.find_next_sibling('p')
            if next_p:
                new_div = soup.new_tag('div', **{'class': 'warning'})

                h3_tag = soup.new_tag('h3')
                h3_tag.string = heading_text
                new_div.append(h3_tag)
                new_div.append(next_p.extract())  #remove p from the original spot

                h2.replace_with(new_div)

    return soup


# def convert_tool(soup):
#     """converts the area with 'tools needed' to the kb required div"""

#     #finds tools anchor
#     anchor = soup.find('a', {'name': 'tools'})
#     if not anchor:
#         return soup  

#     #finds the next h2 after the anchor 
#     h2 = anchor.find_next_sibling('h2')
#     if not h2:
#         return soup

#     #collect all consecutive ul elements after the h2
#     ul_elements = []
#     next_tag = h2.find_next_sibling()
#     while next_tag and next_tag.name == 'ul':
#         ul_elements.append(next_tag)
#         next_tag = next_tag.find_next_sibling()

#     if not ul_elements:
#         return soup 

#     #---make the new div----
#     new_div = soup.new_tag('div', **{'class': 'kb-required'})

#     h3_tag = soup.new_tag('h3')
#     h3_tag.string = 'Supplies:'
#     new_div.append(h3_tag)

#     #make a single consolidated ul
#     consolidated_ul = soup.new_tag('ul')
#     for ul in ul_elements:
#         for li in ul.find_all('li'):
#             consolidated_ul.append(li.extract())  #move li to new ul
#     new_div.append(consolidated_ul)

#     #reaplce the original h2 with the new div
#     h2.replace_with(new_div)

#     anchor.decompose() #remove original anchor

#     for ul in ul_elements: #remove old list
#         ul.decompose()

#     return soup


def convert_tool(soup):
    # Keywords to identify the tools/supplies section
    # This now allows for conversion if the section is just an H2 containing these words
    tool_keywords = re.compile(r'TOOLS|SUPPLIES|PARTS', re.IGNORECASE)
    
    # Find the old anchor structure (if it exists) and remove it immediately
    anchor = soup.find('a', {'name': 'tools'})
    if anchor:
        anchor.decompose()
        
    # Collect all H2 tags that contain the keywords
    h2_sections_to_process = []
    
    # Use list() for iteration as we modify the soup structure later
    for h2 in list(soup.find_all('h2')):
        text = h2.get_text(strip=True)
        if tool_keywords.search(text):
            h2_sections_to_process.append(h2)
            
    # Process the sections
    for h2 in h2_sections_to_process:
        
        # Collect all consecutive <ul> elements after the h2
        ul_elements = []
        next_tag = h2.find_next_sibling()
        while next_tag and next_tag.name == 'ul':
            ul_elements.append(next_tag)
            next_tag = next_tag.find_next_sibling()
            
        if not ul_elements:
            continue # No lists for this H2, skip processing

        # Create the new div
        new_div = soup.new_tag('div', **{'class': 'kb-required'})

        # Add h3 heading (using a generic "Supplies:" title)
        h3_tag = soup.new_tag('h3')
        h3_tag.string = 'Tools:'
        new_div.append(h3_tag)

        # Create a single consolidated <ul>
        consolidated_ul = soup.new_tag('ul')
        for ul in ul_elements:
            for li in ul.find_all('li'):
                consolidated_ul.append(li.extract())  # move <li> to new ul
        new_div.append(consolidated_ul)

        # Replace the original h2 with the new div
        h2.replace_with(new_div)

        # Remove the old <ul> elements
        for ul in ul_elements:
            ul.decompose()

    return soup



def convert_lists_to_steps(soup):
    """
    convert lists to "step" texts
    logic: step # will i++ until h2 anchor is hit. once it hits, it resets step # to 1
    """
    #find all h2 anchors
    h2_section = soup.find_all('h2', class_='kb-anchor')

    for h2 in h2_section:
        step_counter = 1  #reset her every h2 anchor

        #collect siblings until the next h2.kb-anchor
        next_tag = h2.find_next_sibling()
        section_tags = []
        while next_tag:
            #stop when another h2 anchor is found
            if isinstance(next_tag, Tag) and (next_tag.name == 'h2' and 'kb-anchor' in next_tag.get('class', [])):
                break
            if isinstance(next_tag, Tag):
                section_tags.append(next_tag)
            next_tag = next_tag.find_next_sibling()

        #converts all ol to steps
        for ol in [t for t in section_tags if isinstance(t, Tag) and t.name == 'ol']:
            new_nodes = []

            for child in list(ol.children):
                #skip empty text nodes
                if isinstance(child, NavigableString):
                    if not child.strip():
                        continue
                    continue

                contains_special_div = False

                #skips div and tip warning (is child of the step texts)
                if child.name == 'div' and any(cls in ('warning', 'tip') for cls in (child.get('class') or [])):
                    contains_special_div = True

                if not contains_special_div and child.find('div', class_=['warning', 'tip']):
                    contains_special_div = True

                if not contains_special_div and child.name == 'li' and (
                    child.find('div', class_='warning') or child.find('div', class_='tip')
                ):
                    contains_special_div = True

                if contains_special_div:
                    new_nodes.append(child.extract())
                    continue

                #--convert li elements into step paragraphs--
                if child.name == 'li':
                    new_p = soup.new_tag('p')
                    new_p.append(soup.new_string(f"Step {step_counter}: "))

                    #extract img
                    images = child.find_all('img', recursive=True)
                    for img in images:
                        img.extract()

                    for c in list(child.contents):
                        new_p.append(c)

                    #add images at the end
                    for img in images:
                        new_p.append(img)

                    new_nodes.append(new_p)
                    step_counter += 1
                    continue

                #preserve any other tags
                new_nodes.append(child.extract())

            #insert new nodes and remove the old ol tags
            for node in new_nodes:
                ol.insert_before(node)
            ol.decompose()

    return soup




def convert_note_to_tip_div(soup):
    """convert li notes/tip to tip divs"""
    for li in soup.find_all('li'):
        text = li.get_text(strip=True)
        #checks for a pattern match
        if re.match(r'^\s*NOTE\b', text, re.IGNORECASE):
            
            #extract img tag
            images = li.find_all('img', recursive=True)
            for img in images:
                img.extract()

            #clean the text
            cleaned_text = re.sub(r'^\s*NOTE\b\s*', '', text, flags=re.IGNORECASE).strip()

            #--build the tip content--
            tip_div = soup.new_tag('div', **{'class': 'tip'})
            h3_tag = soup.new_tag('h3')
            h3_tag.string = 'Note:'
            p_tag = soup.new_tag('p')
            p_tag.string = cleaned_text
            tip_div.append(h3_tag)
            tip_div.append(p_tag)

            #if img exist, use 2 column
            if images:
                grid_div = soup.new_tag('div', **{
                    'class': 'slds-grid slds-gutters slds-wrap'
                })

                #left column for tip
                left_col = soup.new_tag('div', **{
                    'class': 'slds-col slds-size_1-of-1 slds-medium-size_1-of-2'
                })
                left_col.append(tip_div)

                #right column for img
                right_col = soup.new_tag('div', **{
                    'class': 'slds-col slds-size_1-of-1 slds-medium-size_1-of-2'
                })
                for img in images:
                    right_col.append(img)

                #combine both
                grid_div.append(left_col)
                grid_div.append(right_col)

                #replace li with grid layout
                li.replace_with(grid_div)
            else:
                li.replace_with(tip_div)

    return soup




def convert_li_to_warning_div(soup):
    """convert a listed warning section to a warning div"""

    keyword_pattern = r'^\s*(IMPORTANT|WARNING|DANGER)\b'

    for li in soup.find_all('li'):
        #get the full text of the <li> element, stripping leading/trailing whitespace
        text = li.get_text(strip=True)

        #match if it starts with the pattern
        match = re.match(keyword_pattern, text, re.IGNORECASE)

        if match:
            keyword = match.group(1).capitalize() #'Important' , 'Warning'
            
            #extract img tags
            images = li.find_all('img', recursive=True)
            for img in images:
                img.extract()

            #clean text
            cleaned_text = re.sub(
                r'^\s*' + re.escape(match.group(0).strip()) + r'\s*', 
                '', 
                text, 
                flags=re.IGNORECASE
            ).strip()

            #--build the warning content--
            warning_div = soup.new_tag('div', **{'class': 'warning'})
            h3_tag = soup.new_tag('h3')
            h3_tag.string = f'{keyword}:' 
            p_tag = soup.new_tag('p')
            p_tag.string = cleaned_text
            warning_div.append(h3_tag)
            warning_div.append(p_tag)

            #--iff images exist, use 2-column grid layout--
            if images:
                grid_div = soup.new_tag('div', **{
                    'class': 'slds-grid slds-gutters slds-wrap'
                })

                #left ccolumn for warning text
                left_col = soup.new_tag('div', **{
                    'class': 'slds-col slds-size_1-of-1 slds-medium-size_1-of-2'
                })
                left_col.append(warning_div)

                #right column for images
                right_col = soup.new_tag('div', **{
                    'class': 'slds-col slds-size_1-of-1 slds-medium-size_1-of-2'
                })
                for img in images:
                    right_col.append(img)

                #combine both column
                grid_div.append(left_col)
                grid_div.append(right_col)

                #replace li with grid layout
                li.replace_with(grid_div)
            else:
                #else no image, just extend the div to the whole screen
                li.replace_with(warning_div)

    return soup



def convert_step_p_to_h3(soup):
    step_pattern = re.compile(r'^\s*Step\s*\d+\s*:\s*', re.IGNORECASE)

    for p in soup.find_all('p'):
        if not isinstance(p, Tag):
            continue

        text = p.get_text(strip=True)
        match = step_pattern.match(text)
        
        if match:
            #match the step # prefex "Step.."
            step_prefix = match.group(0).strip()
            
            #find the end of the step prefix text within the tag's content
            full_p_content = str(p)
            
            #use the text content to find the index where the step prefix ends
            start_index_of_content = re.search(re.escape(step_prefix), full_p_content, re.IGNORECASE).end()

            new_h3 = soup.new_tag('h3')
            new_p = soup.new_tag('p')
            
            new_h3.string = step_prefix
            
            #put the <h3> before the old <p>
            p.insert_before(new_h3)

            #move all original content from <p> to new <p>
            #check if the <p> contains only NavigableStrings/Tags that make up the prefix
            if len(p.contents) == 1 and isinstance(p.contents[0], NavigableString):
                #if the content is a single string node, split it manually
                full_string = str(p.contents[0])
                content_part = re.sub(re.escape(step_prefix), '', full_string, flags=re.IGNORECASE, count=1).lstrip()
                
                if content_part.strip():
                    new_p.append(soup.new_string(content_part))
                
            else:
                #else the content has multiple children, so we extract them and re-insert into the new <p>.
                if p.contents and isinstance(p.contents[0], NavigableString):
                    first_string = str(p.contents[0])
                    # Content part is the string after the prefix
                    content_part = re.sub(re.escape(step_prefix), '', first_string, flags=re.IGNORECASE, count=1).lstrip()
                    
                    if content_part.strip():
                        new_p.append(soup.new_string(content_part))
                    
                    #remove old stirng node
                    p.contents[0].extract()

                for child in list(p.contents):
                    new_p.append(child.extract())

            #insert the new <p> after the <h3>
            new_h3.insert_after(new_p)

            p.decompose()

    return soup




# def update_alt_text(soup):
#     images = soup.find_all('img')
    
#     #container to keep track of img counts
#     image_section_counts = {}

#     #helper function to clean file texts
#     def sanitize_text(text):
#         text_cleaned = re.sub(r'^Step \d+:\s*', '', text, flags=re.IGNORECASE).strip()
#         text_cleaned = re.sub(r',', '', text_cleaned)
#         text_cleaned = re.sub(r'\s+', '-', text_cleaned)
#         return text_cleaned.lower()

#     for img in images:
#         prev_h3 = img.find_previous('h3')
#         #find the most recent h2 with kb anchor
#         prev_h2 = img.find_previous('h2', class_='kb-anchor')

#         #the base key for Filename and Counting
#         if prev_h2:
#             #use h2 text for the file base name
#             h2_text = prev_h2.get_text().strip()
#             base_img_key = sanitize_text(h2_text)
#         elif prev_h3:
#             #use h3 if no h2 is found for now
#             h3_text = prev_h3.get_text().strip()
#             base_img_key = sanitize_text(h3_text)
#         else:
#             #default for img outside of this content
#             base_img_key = "general-content"

#         #update and get the current sequential # for this section key
#         if base_img_key not in image_section_counts:
#             image_section_counts[base_img_key] = 1
#         else:
#             image_section_counts[base_img_key] += 1
#         current_img_number = image_section_counts[base_img_key]

#         #make final file name
#         final_filename = f"{base_img_key}-{current_img_number}"

#         #set alt text
#         h3_key_for_alt = prev_h2.get_text().strip() if prev_h3 else base_img_key.replace('-', ' ').title()

#         original_src = img.get('src', '')
#         #reads curr file
#         src_parts_match = re.match(r'^(.*[/])?(.*)(\.[a-zA-Z0-9]+)$', original_src)
        
#         #defaults file to png if extension is not present
#         path_prefix = src_parts_match.group(1) if src_parts_match and src_parts_match.group(1) else ''
#         extension = src_parts_match.group(3) if src_parts_match and src_parts_match.group(3) else '.png'
        
#         # makes new src file path
#         new_src_value = f"{path_prefix}{final_filename}{extension}"
        
#         img['src'] = new_src_value
#         img['alt'] = h3_key_for_alt
#         img['title'] = h3_key_for_alt
           
#     return soup

def update_alt_text(soup):
    images = soup.find_all('img')
    
    # container to keep count of img. Key will be the sanitized H2/Section text.
    image_section_counts = {}

    # Helper function to sanitize text for filename
    def sanitize_text(text):
        # strip "Step X:" prefix if it exists (from H3s)
        text_cleaned = re.sub(r'^Step \d+:\s*', '', text, flags=re.IGNORECASE).strip()
        # remove commas
        text_cleaned = re.sub(r',', '', text_cleaned)
        # replace whitespace with dashes
        text_cleaned = re.sub(r'\s+', '-', text_cleaned)
        return text_cleaned.lower()

    for img in images:
        prev_h3 = img.find_previous('h3')
        # Find the most recent h2 with the class 'kb-anchor' for the section name
        prev_h2 = img.find_previous('h2', class_='kb-anchor')

        # 1. Determine the base key for Filename and Counting
        # The key for counting/filename is still based on H2 (or H3 fallback) to ensure continuity
        if prev_h2:
            # Use H2 text for the file grouping/counting key
            h2_text = prev_h2.get_text().strip()
            base_img_key = sanitize_text(h2_text)
        elif prev_h3:
            # Fallback to H3 text if no H2 is found
            h3_text = prev_h3.get_text().strip()
            base_img_key = sanitize_text(h3_text)
        else:
            # Default key for images outside structured content
            base_img_key = "general-content"

        # 2. Update and get the current sequential number for this section key
        if base_img_key not in image_section_counts:
            image_section_counts[base_img_key] = 1
        else:
            image_section_counts[base_img_key] += 1
        current_img_number = image_section_counts[base_img_key]

        # 3. Construct the final filename: [Section-Name]-[Count]
        # The image filename is now sequential within the scope of the H2 (base_img_key)
        final_filename = f"{base_img_key}-{current_img_number}"

        # 4. Set Alt/Title text (UPDATED to use raw H2 text if available)
        if prev_h2:
            # Use the raw H2 text for the alt/title
            alt_title_text = prev_h2.get_text().strip()
        elif prev_h3:
            # Fallback to raw H3 text if no H2 is found
            alt_title_text = prev_h3.get_text().strip()
        else:
            # Final fallback (should rarely happen in structured docs)
            alt_title_text = "General Content Image"


        # 5. Update image attributes
        original_src = img.get('src', '')
        # reads the current file path
        src_parts_match = re.match(r'^(.*[/])?(.*)(\.[a-zA-Z0-9]+)$', original_src)
        
        # defaults file to png if extension is not present
        path_prefix = src_parts_match.group(1) if src_parts_match and src_parts_match.group(1) else ''
        extension = src_parts_match.group(3) if src_parts_match and src_parts_match.group(3) else '.png'
        
        # makes new src file path
        new_src_value = f"{path_prefix}{final_filename}{extension}"
        
        img['src'] = new_src_value
        img['alt'] = alt_title_text
        img['title'] = alt_title_text
           
    return soup





def remove_first_table_and_keep_content(soup):
    """
    Finds the first <table> in the document, removes it entirely
    (including <tr> and <td> tags), but keeps its inner contents.
    """
    first_table = soup.find('table')
    if not first_table:
        return soup  # No table found

    # Create a list to collect all child elements we want to keep
    preserved_content = []

    # Extract all contents inside <td> and <tr> recursively
    for element in first_table.descendants:
        if isinstance(element, Tag) and element.name in ['p', 'img', 'a']:
            preserved_content.append(element)

    # Insert preserved content right before the table
    for content in preserved_content:
        first_table.insert_before(content)

    # Finally remove the whole table
    first_table.decompose()

    return soup


def remove_comment_links(soup):
    """
    remove the comments
    """
    comment_link_pattern = re.compile(r'^#cmnt_ref\d+$')

    # Use list() to iterate over a copy, as we are modifying the tree structure (decomposing parents)
    for a_tag in list(soup.find_all('a', href=comment_link_pattern)):
        parent = a_tag.parent
        
        # Check if the parent is a paragraph tag
        if parent and parent.name == 'p':
            # Remove the entire parent <p> block, including the link and all text inside.
            parent.decompose()
        else:
            # If not in a <p>, just remove the link tag itself.
            a_tag.decompose()
        
    return soup


def remove_unnecessary_text(soup, unwanted_strings):
    """
    Finds and removes unwanted strings from all texts --> removing typos mostly
    """
    #make regex pattern
    pattern = re.compile('|'.join(re.escape(s) for s in unwanted_strings), re.IGNORECASE)

    #iterates through all the text node
    for text_node in soup.find_all(string=True):
        #avoid text inside script or style tags
        if text_node.parent.name in ['script', 'style']:
            continue
        
        #change the unwanted texts
        original_text = text_node.string
        new_text = pattern.sub('', original_text)
        if new_text != original_text:
            text_node.replace_with(NavigableString(new_text))

    return soup


def separate_img(soup):
    for p_tags in list(soup.find_all('p')):
        images=p_tags.find_all('img')

        for img in reversed(images):
            img.extract()
            p_tags.insert_after(img)

    return soup
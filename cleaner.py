from bs4 import BeautifulSoup, Tag
import os
import re


def remove_br_tags(text):
    return re.sub(r'</?br\s*/?>', '', text, flags=re.IGNORECASE)

def clean_html(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')

    html_content=remove_br_tags(html_content)
    for br_tag in soup.find_all('br'):
        br_tag.decompose()

    #removes the whole <style>
    for style_tag in soup.find_all('style'):
        style_tag.decompose()

    #remove the entire <head> tag
    head_tag = soup.find('head')
    if head_tag:
        head_tag.decompose()

    for img_tag in soup.find_all('img'):
        parent_p = img_tag.find_parent('p')
        if parent_p:
            #check if the sibling before the image has a step header
            
            #find the elelment containing the step text, usually first child of >p> 
            step_text_element = parent_p.contents[0] if parent_p.contents else None
            
            #if the step text and the image are direct children of the same <p>
            if step_text_element and step_text_element != img_tag:
                #create a new p tag for the step text
                new_p = soup.new_tag('p')
                
                #unwrap the image's immediate span parent if it exists
                parent_span = img_tag.find_parent('span')
                if parent_span:
                    parent_span.unwrap()

                #extract img
                extracted_img = img_tag.extract()
                
                #get all remaining elements (text/spans)
                content_to_move = list(parent_p.contents)
                for content in content_to_move:
                    new_p.append(content.extract())
                
                #insert the new p tag with the text before the original p tag (which will now be removed or empty)
                parent_p.insert_before(new_p)
                
                #insert imgafter the new p tag
                new_p.insert_after(extracted_img)
                
                #if p empty decompose it
                if not parent_p.get_text(strip=True) and not parent_p.find('img'):
                    parent_p.decompose()

    #unwrap all span tag while keeping the content
    for span in soup.find_all('span'):
        span.unwrap()

    #remove these attributes
    attributes_to_remove = ['id', 'style', 'title', 'class', 'colspan', 'rowspan']
    for tag in soup.find_all(True):
        #keep 'class' on div tags
        if tag.name != 'div' and 'class' in tag.attrs:
            del tag.attrs['class']
        
        # remove the rest
        for attr in attributes_to_remove:
            if attr in tag.attrs and attr != 'class':
                del tag.attrs[attr]

    #Remove all span tags while keeping their contents
    for span in soup.find_all('span'):
        span.unwrap()

    # Remove div tags and their content only if they are empty
    for div in soup.find_all('div'):
        if not div.get_text(strip=True) and not div.find('img'):
            div.decompose()
        else:
            div.unwrap()
    
    #remove any text that inclues 'updated'
    for p_tag in soup.find_all('p'):
        # The regular expression matches "Updated" followed by a number and an optional colon.
        if re.search(r'^Updated\s*\d+', p_tag.get_text(strip=True)):
            p_tag.decompose()

    #removes empty html tables
    for table in soup.find_all('table'):
        if not table.get_text(strip=True):
            table.decompose()
        
    #remove empty p tags
    for p in soup.find_all('p'):
        if not p.get_text(strip=True):
            p.decompose()

    #replace &nbsp; with a regular space
    # attempting to remove extra whitespace
    for text_node in soup.find_all(string=True):
        # 1. Replace non-breaking spaces with standard spaces
        clean_text = text_node.replace("\xa0", " ")
        normalized_text = " ".join(clean_text.split())
        
        text_node.replace_with(normalized_text)


    for h1_tag in soup.find_all('h1'):
        #chekc if emoty and has img
        if not h1_tag.get_text(strip=True) and h1_tag.find('img'):
            h1_tag.unwrap()


    #unwrap body and html tags
    if soup.body:
        soup.body.unwrap()
    if soup.html:
        soup.html.unwrap()

    #make new divs
    new_div = soup.new_tag("div", **{'class': 'article-body'})

    new_h1 = soup.new_tag("h1", **{'class': 'article-title invisible'})
    new_h1.string = "Title"
    
    new_p = soup.new_tag("p", **{'class': 'article-summary invisible'})
    new_p.string = "Summary"

    new_div.append(new_h1)
    new_div.append(new_p)

    #move all existing content into the new div
    content_to_wrap = list(soup.contents)
    for element in content_to_wrap:
        new_div.append(element)
    
    #replace the original ontents with just the new div
    soup.clear()
    soup.append(new_div)

    return str(soup.prettify())


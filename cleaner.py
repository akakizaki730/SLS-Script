from bs4 import BeautifulSoup, Tag
import re


def remove_br_tags(text: str) -> str:
    """Remove <br> tags from an HTML string (case-insensitive)."""
    return re.sub(r'</?br\s*/?>', '', text, flags=re.IGNORECASE)


def separate_h1_img(soup: BeautifulSoup) -> None:
    """Move images out of empty <h1> tags so they appear after the heading.
    """
    for h1_tag in list(soup.find_all('h1')):
        images = h1_tag.find_all('img')
        for img in reversed(images):
            extracted_img = img.extract()
            h1_tag.insert_after(extracted_img)


def clean_html(html_content: str) -> str:
    """
    cleans and reformats HTML content according to specified rules.
    minimizes the number of full-tree passes 
    """
    #removes<br> before parsing 
    html_content = remove_br_tags(html_content)
    soup = BeautifulSoup(html_content, 'html.parser')

    for tag in soup.find_all(['style', 'head']):
        tag.decompose()

    for br in soup.find_all('br'):
        br.decompose()

    #move images out of <p> elements that also contain text.
    for img in list(soup.find_all('img')):
        parent_p = img.find_parent('p')
        if not parent_p:
            continue

        #if the <p> contains non-image text or other elements besides this image,
        #create a new <p> with that content and move the image after it.
        contents = parent_p.contents
        # If there is any non-empty text or non-img tag besides this img:
        has_other_content = any(
            (isinstance(c, str) and c.strip()) or (isinstance(c, Tag) and c.name != 'img')
            for c in contents if c is not img
        )

        if has_other_content:
            #unwrap span parent of image if present (keeps inner HTML)
            span_parent = img.find_parent('span')
            if span_parent:
                span_parent.unwrap()

            extracted_img = img.extract()
            new_p = soup.new_tag('p')
            for c in list(parent_p.contents):
                new_p.append(c.extract())
            parent_p.insert_before(new_p)
            new_p.insert_after(extracted_img)

            # remove the original p if now empty
            if not parent_p.get_text(strip=True) and not parent_p.find('img'):
                parent_p.decompose()

    #single pass to handle spans, attributes and divs
    attrs_to_remove = {'id', 'style', 'title', 'colspan', 'rowspan'}
    for tag in list(soup.find_all(True)):
        # Unwrap spans (keep their contents)
        if tag.name == 'span':
            tag.unwrap()
            continue

        #for divs: remove them only if empty and without images; otherwise keep and
        #clean attributes but preserve their 'class'.
        if tag.name == 'div':
            if not tag.get_text(strip=True) and not tag.find('img'):
                tag.decompose()
                continue
            # remove unwanted attributes but preserve 'class'
            for a in list(tag.attrs):
                if a in attrs_to_remove:
                    del tag.attrs[a]
            continue

        # For other tags: remove unwanted attributes and remove 'class' too
        for a in list(tag.attrs):
            if a in attrs_to_remove or a == 'class':
                del tag.attrs[a]

    # Remove P tags that begin with "Updated <number>"
    for p_tag in list(soup.find_all('p')):
        if re.search(r'^Updated\s*\d+', p_tag.get_text(strip=True)):
            p_tag.decompose()

    # Remove empty tables and empty paragraphs
    for table in list(soup.find_all('table')):
        if not table.get_text(strip=True):
            table.decompose()

    for p in list(soup.find_all('p')):
        if not p.get_text(strip=True):
            p.decompose()

    # Normalize text nodes: replace NBSP and collapse whitespace
    for text_node in list(soup.find_all(string=True)):
        # skip script/style content (already removed earlier, but keep safe)
        if text_node.parent and text_node.parent.name in ('script', 'style'):
            continue
        clean_text = text_node.replace('\xa0', ' ')
        normalized = ' '.join(clean_text.split())
        if normalized != text_node:
            text_node.replace_with(normalized)

    # Unwrap empty H1 that only contains an image
    for h1_tag in list(soup.find_all('h1')):
        if not h1_tag.get_text(strip=True) and h1_tag.find('img'):
            h1_tag.unwrap()

    # Unwrap html/body wrappers if present
    if soup.body:
        soup.body.unwrap()
    if soup.html:
        soup.html.unwrap()

    separate_h1_img(soup)

    # Wrap everything in a single article-body div with placeholder title/summary
    new_div = soup.new_tag('div', **{'class': 'article-body'})
    new_h1 = soup.new_tag('h1', **{'class': 'article-title invisible'})
    new_h1.string = 'Title'
    new_p = soup.new_tag('p', **{'class': 'article-summary invisible'})
    new_p.string = 'Summary'
    new_div.append(new_h1)
    new_div.append(new_p)

    # Move remaining content into the new div
    for element in list(soup.contents):
        new_div.append(element.extract())

    soup.clear()
    soup.append(new_div)

    return str(soup.prettify())


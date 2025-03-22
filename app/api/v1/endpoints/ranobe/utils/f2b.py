import base64
from lxml import etree


class FB2Builder:
    def __init__(self, title: str) -> None:
        self.root = etree.Element('FictionBook', nsmap={
            None: 'http://www.gribuser.ru/xml/fictionbook/2.0',
            'l': 'http://www.w3.org/1999/xlink'})
        self.description = etree.SubElement(self.root, 'description')
        self.title_info = etree.SubElement(self.description, 'title-info')
        self.create_title(title)
        self.body = etree.SubElement(self.root, 'body')
        self.section_cache = {}

    def create_title(self, title: str) -> None:
        title_element = etree.SubElement(self.title_info, 'book-title')
        title_element.text = title

    def add_section(self, title: str) -> etree.Element:
        section = etree.SubElement(self.body, 'section')
        title_element = etree.SubElement(section, 'title')
        p = etree.SubElement(title_element, 'p')
        p.text = title
        return section

    def add_paragraph(self, section: etree.Element, text: str) -> None:
        p = etree.SubElement(section, 'p')
        p.text = text

        return p

    def add_empty_line(self, section: etree.Element) -> None:
        empty_line = etree.SubElement(section, 'empty-line')

        return empty_line

    def add_image(self, section: etree.Element, media_id: str) -> None:
        media_id = f"img_{media_id}"
        nsmap = {'l': 'http://www.w3.org/1999/xlink'}
        href_attrib = f"{{{nsmap['l']}}}href"
        etree.SubElement(section, 'image', **{href_attrib: f"#{media_id}"})

    def add_binary(self, section: etree.Element, media_id: str, data: str) -> None:
        nsmap = {'l': 'http://www.w3.org/1999/xlink'}
        href_attrib = f"{{{nsmap['l']}}}href"
        content_type_attrib = 'content-type'
        base64_img = base64.b64encode(data).decode('utf-8')

        binary = etree.SubElement(
            self.root,
            'binary',
            id=f'img_{media_id}',
            **{content_type_attrib: "image/jpeg"},
        )
        binary.text = base64_img

    def generate(self) -> str:
        return '<?xml version="1.0" encoding="UTF-8"?>\n' + etree.tostring(self.root, pretty_print=True,
                                                                           encoding='utf-8').decode('utf-8')

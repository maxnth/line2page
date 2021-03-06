import glob
import getpass
import os
import argparse
from datetime import datetime
from PIL import Image, ImageDraw
from xml.etree.ElementTree import Element, SubElement, Comment, tostring
from xml.etree import ElementTree

# noinspection PyUnresolvedReferences
from xml.dom import minidom


gtList = []
imgList = []
nameList = []
pairing = []
matches = []
lines = 20
pages = []
border = 10
spacer = 5
iterative = True
pageIterator = 0

source = ""
dest = ""
pred = False
debug = False

img_ext = '.nrm.png'
xmlSchemaLocation = 'http://schema.primaresearch.org/PAGE/gts/pagecontent/2017-07-15 http://schema.primaresearch.org/PAGE/gts/pagecontent/2017-07-15/pagecontent.xsd'

def main():

    parser = make_parser()
    parse(parser.parse_args())

    os.chdir(source)
    cwd = os.getcwd()
    print(cwd)
    getfiles()
    matchfiles()
    # print(matches)
    global pages
    pages = list(chunks(matches, lines))
    for page in pages:
        makepage(page)

    #makepage(pages[0])
    #makepage(pages[1])


def make_parser():
    parser = argparse.ArgumentParser(description='python script to merge GT lines to page images and xml')
    parser.add_argument('-s',
                        '--source-folder',
                        action='store',
                        dest='source_path',
                        default='./',
                        required=True,
                        help='Path to images and GT')
    parser.add_argument('-d',
                        '--dest-folder',
                        action='store',
                        dest='dest_path',
                        default='merged/',
                        required=True,
                        help='Path to merge objects')

    parser.add_argument('-e',
                        '--ext',
                        action='store',
                        dest='img_ext',
                        default='.nrm.png',
                        help='image extension')

    parser.add_argument('-p',
                        '--pred',
                        action='store_true',
                        dest='pred',
                        default=False,
                        help='Set Flag to also store .pred.txt')

    parser.add_argument('-l',
                        '--lines',
                        action='store',
                        dest='lines',
                        type=int,
                        default=20,
                        help='lines per page')

    parser.add_argument('-ls',
                        '--line-spacing',
                        action='store',
                        dest='spacing',
                        type=int,
                        default=5,
                        help='line spacing')

    parser.add_argument('-b',
                        '--border',
                        action='store',
                        dest='border',
                        type=int,
                        default=10,
                        help='border in px')
    parser.add_argument('--debug',
                        action='store_true',
                        dest='debug',
                        default=False,
                        help='prints debug xml')
    return parser


def parse(args):
    global source
    source = args.source_path
    global dest
    dest = args.dest_path
    global img_ext
    img_ext = args.img_ext
    global pred
    pred = args.pred
    global lines
    lines = args.lines
    global spacer
    spacer = args.spacing
    global border
    border = args.border
    global debug
    debug = args.debug


def getfiles():
    global imgList
    global gtList
    imgList = [f for f in sorted(glob.glob('*' + img_ext))]
    gtList = [f for f in glob.glob("*.gt.txt")]


def matchfiles():
    for img in imgList:
        name = img.split('.')[0]
        nameList.append(name)
        pairing.append(img)
        gt_filename = [f for f in glob.glob(name + ".gt.txt")][0]
        pairing.append(gt_filename)
        pairing.append(get_text(gt_filename))
        pred_filename = [f for f in glob.glob(name + ".pred.txt")][0]
        pairing.append(pred_filename)
        pairing.append(get_text(pred_filename))
        matches.append(pairing.copy())
        pairing.clear()


def get_text(filename):
    with open(filename, 'r') as myfile:
        data = myfile.read().rstrip()
        return data


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def makepage(page):
    if iterative:
        global pageIterator
        pageIterator += 1
        name = str(pageIterator).zfill(4)
    else:
        name = page[0][0].split(".")[0] + "-" + page[-1][0].split(".")[0]
    merged = merge_images(page)
    global dest
    if not os.path.exists(dest):
        #print(dest + "dir not found, creating directory")
        os.mkdir(dest)

    if not dest.endswith(os.path.sep):
        dest += os.path.sep
    merged.save(dest + name + img_ext)
    xml_tree = build_xml(page, name + img_ext, merged.height, merged.width)
    if debug:
        print(prettify(xml_tree))
    xml = ElementTree.tostring(xml_tree, 'utf8', 'xml')
    myfile = open(dest + name + ".xml", "wb")
    myfile.write(xml)

    #xml.save("merged/" + name + ".xml")


def merge_images(list):
    """Merge list of images into one, displayed on top of each other
    :return: the merged Image object
    """

    imglist = []
    imgwidth = 0
    imgheight = 0
    spacer_height = spacer * (len(list)-1)

    for i in list:
        #print(i)
        image = Image.open(i[0])
        (width,height) = image.size
        imgwidth = max(imgwidth, width)
        imgheight += height
        imglist.append(image)

    result = Image.new('RGB', (imgwidth + border*2, imgheight + border*2 + spacer_height),(255,255,255))
    before = border

    for img in imglist:
        #print(before)
        result.paste(img, (border,before))
        (pw,ph) = img.size
        before += img.size[1] + spacer
    return result


def build_xml(line_list,img_name, img_height, img_width):
    """Builds PageXML from list of images, with txt files corresponding to each one of them
    :return: the built PageXml[.xml] file
    """
    pcgts = Element('PcGts')
    pcgts.set('xmlns', 'http://schema.primaresearch.org/PAGE/gts/pagecontent/2017-07-15')
    pcgts.set('xmlns:xsi', 'http://www.w3.org/2001/XMLSchema-instance')
    pcgts.set('xsi:schemaLocation', xmlSchemaLocation)

    metadata = SubElement(pcgts, 'Metadata')
    creator = SubElement(metadata, 'Creator')
    creator.text = getpass.getuser()
    created = SubElement(metadata, 'Created')
    generated_on = str(datetime.now())
    created.text = generated_on
    last_change = SubElement(metadata,'LastChange')
    last_change.text = generated_on

    page = SubElement(pcgts, 'Page')
    page.set('imageFilename',img_name)
    page.set('imageHeight', str(img_height))
    page.set('imageWidth', str(img_width))

    text_region = SubElement(page,'TextRegion')
    text_region.set('id', 'r0')
    text_region.set('type', 'paragraph')
    region_coords = SubElement(text_region, 'Coords')
    s = str(border)
    coord_string = s + ',' + s + ' ' + s + "," + str(img_height - border) + ' ' + str(img_width - border) + ',' + str(img_height - border) + ' ' + str(img_width - border) + ',' + s
    region_coords.set('points', coord_string)
    i = 1
    last_bottom = border
    for line in line_list:
        text_line = SubElement(text_region, 'TextLine')
        text_line.set('id', 'r0_l' + str(line[0].split('.')[0].zfill(3)))
        i += 1
        line_coords = SubElement(text_line,'Coords')
        image = Image.open(line[0])
        (width, height) = image.size
        line_coords.set('points', make_coord_string(last_bottom, width, height))
        last_bottom += (height+spacer)
        line_gt_text = SubElement(text_line, 'TextEquiv')
        line_gt_text.set('index', str(0))
        unicode_gt = SubElement(line_gt_text, 'Unicode')
        unicode_gt.text = line[2]
        if pred:
            line_pred_text = SubElement(text_line, 'TextEquiv')
            line_pred_text.set('index', str(1))
            unicode_pred = SubElement(line_pred_text, 'Unicode')
            unicode_pred.text = line[4]

    return pcgts


def make_coord_string(previous_lower_left, line_width, line_height):
    b = str(border)
    s = str(spacer)
    p = str(previous_lower_left)
    w = str(line_width + border)
    h = str(line_height + previous_lower_left)
    coord_string = b + ',' + p + ' ' + b + "," + h + ' ' + w + ',' + h + ' ' + w + ',' + p
    return coord_string


def prettify(elem):
    """Return a pretty-printed XML string for the Element.
    """
    rough_string = ElementTree.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml("  ")


if __name__ == "__main__":
    main()

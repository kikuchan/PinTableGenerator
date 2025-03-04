# Pin Table Generator
# Copyright 2022 Kenta Ida
# SPDX-License-Identifier: BSL-1.0
#

from typing import Tuple, Dict, Union
import svgwrite

def __conv_to_svg_color(color: Union[int,str]) -> str:
    return f'#{color:06X}' if type(color) == 'int' else color

def find_free_pin(pin_map, x_max, y_max):
    for cx in range(0, x_max + 1):
        for cy in (range(0, y_max) if cx % 2 == 0 else reversed(range(0, y_max))):
            found = False
            if not (cx, cy) in pin_map:
                return cx * y_max + cy + 1 # +1 for pin number

    raise RuntimeError('No room...')

def assign_pin(pin_map, pin, x_max, y_max, auto_pin_assign = False):
    pin_num = pin.get('pin_number') or (auto_pin_assign and find_free_pin(pin_map, x_max, y_max))

    if not pin_num:
        return False

    x = (pin_num - 1) // y_max;
    y = (pin_num - 1) % y_max;

    pin_map.update({(x, y): pin})

    return True

def compute_pin_map(pin_definitions, x_max, y_max):
    pin_map = {}

    for pin in filter(lambda x: 'pin_number' in x, pin_definitions):
        assign_pin(pin_map, pin, x_max, y_max)

    for pin in filter(lambda x: not 'pin_number' in x, pin_definitions):
        assign_pin(pin_map, pin, x_max, y_max, True)

    return pin_map


def generate_pin_map_svg(pin_definitions: Tuple[Dict[str, str]], number_of_columns:int, number_of_rows:int, pin_type_colors: Dict[str, int], usage_type_colors: Dict[str, int], pin_name_column_width:int = 40, usage_column_width:int = 80, row_height = 20, column_spacing = 0, span_pin_name_without_usage:bool = True) -> svgwrite.Drawing:
    column_width = pin_name_column_width + usage_column_width
    
    number_of_rows = number_of_rows or (len(pin_definitions) + number_of_columns - 1) // number_of_columns;
    total_width = (column_width + column_spacing) * number_of_columns - column_spacing
    total_height = row_height * number_of_rows
    drawing = svgwrite.Drawing(size=(total_width, total_height))
    
    for (column_index, row_index), pin_definition in compute_pin_map(pin_definitions, number_of_columns, number_of_rows).items():
        x = (column_width + column_spacing) * column_index
        y = row_height * row_index

        pin_type = pin_definition['type']
        pin_usage = pin_definition.get('usage')
        pin_usage_type = pin_definition.get('usage_type')
        pin_color = pin_type_colors.get(pin_type, ('black', 'white'))
        fill = __conv_to_svg_color(pin_color[0])
        text_color = __conv_to_svg_color(pin_color[1])
        
        span_pin_cell = span_pin_name_without_usage and pin_usage is None
        pin_name_cell_width = column_width if span_pin_cell else pin_name_column_width
        pin_start_x = x if column_index == 0 or span_pin_cell else x + usage_column_width
        rect = drawing.rect(insert=(pin_start_x, y), size=(pin_name_cell_width, row_height), fill=fill)
        drawing.add(rect)
        text = drawing.text(pin_definition['pin'], insert=(pin_start_x+pin_name_cell_width/2, y+row_height/2), style='text-anchor:middle; dominant-baseline:central', fill=text_color)
        drawing.add(text)

        if pin_usage is not None:
            usage_start_x = x + pin_name_column_width if column_index == 0 else x
            usage_color = usage_type_colors[pin_usage_type]
            usage_fill = __conv_to_svg_color(usage_color[0])
            usage_text_color = __conv_to_svg_color(usage_color[1])
            rect = drawing.rect(insert=(usage_start_x, y), size=(usage_column_width, row_height), fill=usage_fill)
            drawing.add(rect)
            text = drawing.text(pin_usage, insert=(usage_start_x+usage_column_width/2, y+row_height/2), style='text-anchor:middle; dominant-baseline:central', fill=usage_text_color)
            drawing.add(text)

    return drawing

def generate_pin_map_svg_from_json(def_json_path: str, color_json_path: str, **kwargs) -> svgwrite.Drawing:
    import json5
    with open(def_json_path, 'r') as f:
        definitions = json5.load(f)
    with open(color_json_path, 'r') as f:
        colors = json5.load(f)
    
    return generate_pin_map_svg(definitions['pin_definitions'], definitions.get('columns', 2), definitions.get('rows', 0), colors['pin_type_colors'], colors['usage_type_colors'], **kwargs)

if __name__ == '__main__':
    import sys
    import os
    from optparse import OptionParser
    parser = OptionParser()
    parser.set_usage("pin_table_gen.py DEF_JSON COLOR_JSON [options]")
    parser.add_option('-o', "--output", dest="output_file", help="output file name", metavar="OUTPUT")
    parser.add_option("--pin_name_column_width", type="int", dest="pin_name_column_width", help="column width of the pin width column", metavar="PIN_NAME_COLUMN_WIDTH", default=40)
    parser.add_option("--usage_column_width", type="int", dest="usage_column_width", help="column width of the table for the usage cell", metavar="USAGE_COLUMN_WIDTH", default=80)
    parser.add_option("--column_spacing", type="int", dest="column_spacing", help="space between columns", metavar="COLUMN_SPACING", default=0)
    parser.add_option('--row_height', type="int", dest="row_height", help="row height of the table", metavar="ROW_HEIGHT", default=20)
    parser.add_option('--span_pin_name_without_usage', dest="span_pin_name_without_usage", help="spans pin name column if the pin does not define any usages.", default=False, action="store_true")
    (option, args) = parser.parse_args()
    if len(args) < 2:
        parser.print_help()
        sys.exit(1)
    def_json_path = args[0]
    color_json_path = args[1]
    output_path = os.path.splitext(args[0])[0] + '.svg' if option.output_file is None else option.output_file

    optional_args = {}
    optional_args['pin_name_column_width'] = option.pin_name_column_width
    optional_args['usage_column_width'] = option.usage_column_width
    optional_args['column_spacing'] = option.column_spacing
    optional_args['row_height'] = option.row_height
    optional_args['span_pin_name_without_usage'] = option.span_pin_name_without_usage
    
    drawing = generate_pin_map_svg_from_json(def_json_path, color_json_path, **optional_args)
    drawing.saveas(output_path)

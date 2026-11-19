import inspect
import os
from typing import get_origin, List
import xml.etree.ElementTree as ET
from xml.dom import minidom
import xarray as xr
from pathlib import Path

import operations
from meta import REGISTERED_OPERATIONS

OUTPUT_TOOLS_DIR = "mytools"
LOCAL_TOOL_CONF = "local_tool_conf.xml"

def map_type_to_galaxy(param_name, param):
    annotation = param.annotation
    default = param.default if param.default is not inspect.Parameter.empty else None
    origin = get_origin(annotation)

    attrs = {"name": param_name, "label": param_name.replace("_", " ").capitalize()}

    if annotation == xr.Dataset:
        attrs.update({"type": "data", "format": "json"})
    elif origin is list or origin is List:
        attrs.update({"type": "data", "format": "json", "multiple": "true"})
    elif annotation == float:
        attrs.update({"type": "float", "value": str(default or 0.0)})
    elif annotation == int:
        attrs.update({"type": "integer", "value": str(default or 0)})
    elif annotation == bool:
        attrs.update({"type": "boolean", "checked": "true" if default else "false"})
    else:
        attrs.update({"type": "text", "value": str(default or "")})

    return ET.Element("param", attrs)

def generate_tool_xml(op_info):
    func_name = op_info["name"]
    desc = op_info["description"].strip()
    sig = op_info["signature"]

    # main tag <tool>
    tool = ET.Element("tool", id=func_name, name=func_name.replace("_", " ").title(), version="1.0.0")

    # subtag <description>
    ET.SubElement(tool, "description").text = desc

    # preparing for <command> tag
    cmd_lines = [f"python '$__tool_directory__/runner.py' {func_name}"]

    # subtag <inputs>
    inputs_elem = ET.SubElement(tool, "inputs")
    
    for p_name, param in sig.parameters.items():
        # append parameter <param> to inputs
        inputs_elem.append(map_type_to_galaxy(p_name, param))
        
        # add to command line argument
        origin = get_origin(param.annotation)
        if origin is list or origin is List:
            # list of datasets is handled differently
            cmd_lines.append(f'--{p_name} \'#echo " ".join([str($x) for $x in ${p_name}])#\'')
        else:
            cmd_lines.append(f"--{p_name} '${p_name}'")

    cmd_lines.append("--output-json '$output'")

    # subtag <outputs> and <data>
    outputs_elem = ET.SubElement(tool, "outputs")
    ET.SubElement(outputs_elem, "data", name="output", format="json", label=f"{func_name} on $input_json.name" if "input_json" in sig.parameters else f"{func_name} output")

    # subtag <command>
    command_elem = ET.SubElement(tool, "command", detect_errors="exit_code")
    cmd_text = "\n" + " ".join(cmd_lines) + "\n"

    # subtag <help>
    help_elem = ET.SubElement(tool, "help")
    help_elem.text = desc or f"Automatically generated Galaxy tool for operation {func_name}."

    # pretty-print the XML
    raw_xml = ET.tostring(tool, encoding="utf-8")
    parsed = minidom.parseString(raw_xml)

    # add CDATA section for command
    cmd_node = parsed.getElementsByTagName("command")[0]
    cdata = parsed.createCDATASection(cmd_text)
    cmd_node.appendChild(cdata)

    return parsed.toprettyxml(indent="    ")

def generate_local_tool_conf(registered_ops):
    toolbox = ET.Element("toolbox", monitor="true")
    section = ET.SubElement(
        toolbox, "section", id="custom_s3_tools", name="S3 Dask Tools"
    )

    for op_name in registered_ops.keys():
        tool_file_path = f"mytools/tool_{op_name}.xml"
        ET.SubElement(section, "tool", file=tool_file_path)

    raw_xml = ET.tostring(toolbox, encoding="utf-8")
    return minidom.parseString(raw_xml).toprettyxml(indent="    ")

def main():
    output_dir = Path("mytools")
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Found {len(REGISTERED_OPERATIONS)} operations to export to Galaxy XML.")
    for name, op_info in REGISTERED_OPERATIONS.items():
        xml_content = generate_tool_xml(op_info)
        file_path = output_dir / f"tool_{name}.xml"
        file_path.write_text(xml_content, encoding="utf-8")
        print(f" -> Generated file: {file_path}")

    conf_content = generate_local_tool_conf(REGISTERED_OPERATIONS)
    with open(LOCAL_TOOL_CONF, "w", encoding="utf-8") as f:
        f.write(conf_content)
    print(f" -> Generated tool configuration file: {LOCAL_TOOL_CONF}")

if __name__ == "__main__":
    main()

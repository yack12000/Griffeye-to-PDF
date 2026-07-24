#!/usr/bin/env python3

import os
import sys
from pathlib import Path

# Allow Playwright browsers to be loaded from EXE directory
if getattr(sys, 'frozen', False):
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = os.path.join(os.path.dirname(sys.executable), "ms-playwright")


from playwright.sync_api import sync_playwright
# for offline use, copy ms-playwright folder to this location -> C:\Users\<YourUser>\AppData\Local\

def generate_pdf(html_path, pdf_file):

    try:
        with sync_playwright() as p:

            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--disable-gpu",
                    "--no-sandbox",
                    "--disable-dev-shm-usage"
                ]
            )

            page = browser.new_page()
            page.set_viewport_size({"width": 6000, "height": 3000})

            page.goto(Path(html_path).resolve().as_uri(), wait_until="load")
            page.wait_for_timeout(3000)

            # Extract Case Name and Investigator from Griffeye report
            metadata = page.evaluate("""
            () => {
                if (!window.caseData || !window.caseData.metaData)
                    return {caseName: "Unknown Case", investigator: "Unknown"};

                const meta = window.caseData.metaData;

                return {
                    caseName: meta.casename ? meta.casename.value : "Unknown Case",
                    investigator: meta.name ? meta.name.value : "Unknown"
                };
            }
            """)

            case_name = metadata["caseName"]
            investigator = metadata["investigator"]
            print(f"Case Name: {case_name}")
            print(f"Investigator: {investigator}")

            result = page.evaluate("""
            () => {

                const data = window.caseData;
                if (!data || !data.rows) return {cols:10};

                let visibleColumns = [];

                data.columns.forEach(group=>{
                    group.columns.forEach(col=>{
                        if(col.initiallyVisible) visibleColumns.push(col);
                    });
                });

                let table = "<table border='1' style='border-collapse:collapse;width:100%;font-size:10px'>";

                table += "<thead><tr>";
                visibleColumns.forEach(col=>{
                    table += `<th>${col.displayName}</th>`;
                });
                table += "</tr></thead>";

                table += "<tbody>";

                data.rows.forEach(row=>{
                    table += "<tr>";

                    visibleColumns.forEach((col)=>{

                        let value = row[col.name] || "";

                        if(col.name === "Miniature" && value){
                            table += `<td class="thumb">
                            <img src="data:image/png;base64,${value}">
                            </td>`;
                        }
                        else{
                            table += `<td>${value}</td>`;
                        }

                    });

                    table += "</tr>";
                });

                table += "</tbody></table>";

                document.body.innerHTML = table;

                return {cols: visibleColumns.length};
            }
            """)

            column_count = result["cols"]

            # Auto width scaling
            pdf_width = max(17, column_count * 1.8)

            zoom_level = min(1, 14 / column_count)
            page.evaluate(f"() => document.body.style.zoom = '{zoom_level}'")

            # Print CSS
            page.add_style_tag(content="""
            @media print {

                table {
                    table-layout: fixed !important;
                    border-collapse: collapse;
                    page-break-inside: auto;
                }

                thead {
                    display: table-header-group;
                }

                tfoot {
                    display: table-footer-group;
                }

                tr {
                    page-break-inside: avoid;
                    page-break-after: auto;
                }

                th:first-child,
                td:first-child {
                    width: 120px !important;
                    min-width: 120px !important;
                    text-align: center;
                }

                td.thumb img {
                    max-width: 110px;
                    max-height: 90px;
                    display: block;
                    margin: auto;
                }

                td, th {
                    word-wrap: break-word;
                    padding: 4px;
                }

                th {
                    background-color: #eeeeee;
                }
            }
            """)
            page.emulate_media(media="print")
            page.pdf(
                path=pdf_file,
                height=f"{pdf_width}in",
                landscape=True,
                print_background=True,
                display_header_footer=True,

                header_template=f"""
                <div style="font-size:10px;width:100%;padding-left:20px;padding-right:20px;">
                    <span><b>Case:</b> {case_name}</span>
                    <span style="margin-left:40px;"><b>Investigator:</b> {investigator}</span>
                </div>
                """,

                footer_template="""
                <div style="font-size:9px;width:100%;text-align:center;">
                    Page <span class="pageNumber"></span> of <span class="totalPages"></span>
                </div>
                """,


                margin={
                    "top": "60px",
                    "bottom": "60px",
                    "left": "20px",
                    "right": "20px"
                }
            )

            browser.close()

        print(f"PDF successfully generated: {pdf_file}")
        print(f"Detected columns: {column_count}")
        print(f"PDF Width: {pdf_width}")
    except Exception as e:
        print(f"Unable to generate PDF: {e}")
        sys.exit(1)


def main():
    if len(sys.argv) != 3:
        print("Usage: griffeye_to_pdf.py input.html output.pdf")
        sys.exit(1)
    generate_pdf(sys.argv[1], sys.argv[2])


if __name__ == "__main__":
    main()

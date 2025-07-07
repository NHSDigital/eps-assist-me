import csv

file_paths = ["./querytool/eps_assist/preprocessors/prescribing_scal.csv",
              "./querytool/eps_assist/preprocessors/dispensing_scal.csv"]


file_paths = ["./querytool/eps_assist/preprocessors/prescribing_scal.csv"]


def clean_texts(texts: list[str]) -> str:
    return " ".join([clean_text(text) for text in texts])


def clean_text(text: str) -> str:
    text = text.replace("•", "*")

    text = text.replace("\n", " ")

    text = text.replace("¥", "*")

    return text.strip()


def process_file(path: str) -> str:

    doc = []

    with open(path, encoding='ISO8859') as csvfile:
        scalreader = csv.reader(csvfile, delimiter=',', quotechar='"')
        requirement_section = "n/a"

        for row in scalreader:

            # SCAL as changed format (And may change again)
            if "prescribing_scal" in path:
                section_id, item, detail, helpful_docs, risk_logs, assessment_type = row
                # print (section_id, item, detail, helpful_docs, risk_logs, assessment_type)

                is_numeric_section = any(chr.isdigit() for chr in section_id)
                is_top_level = len(section_id) <= 3

                if not is_numeric_section or "Technical Conformance Requirements" in section_id:
                    # discard rows that don't contain a section id
                    continue

                if is_top_level:
                    requirement_section = section_id
                    pass
                else:

                    doc.append(
                        clean_texts(
                            [section_id, item, detail, ". Related docs: ", helpful_docs, ". Risk Logs: ", risk_logs, ". Requirement assessed by: ", assessment_type]
                        )
                    )
                continue

            if len(row) == 6:
                section_id, requirement_or_section, risks, info, _, related_desc = row
            elif len(row) == 7:
                section_id, requirement_or_section, risks, info, _, related_desc, _ = row
            else:
                raise Exception("the input csv had a different number of columns than expected")

            is_numeric_section = any(chr.isdigit() for chr in section_id)
            is_top_level = len(section_id) <= 3

            if not is_numeric_section:
                # discard rows that don't contain a section id
                continue

            if is_top_level:
                requirement_section = requirement_or_section
            else:
                if len(related_desc) > 0:
                    doc.append(
                        f"SCAL Requirement {section_id} {clean_text(requirement_section)}: {clean_text(requirement_or_section)} related info: {bullet_points_to_sentences(related_desc)}"
                    )
                else:
                    doc.append(
                        f"SCAL Requirement {section_id} {clean_text(requirement_section)}: {clean_text(requirement_or_section)}"
                    )

    return "\n\n".join(doc)


if __name__ == "__main__":

    import os
    cwd = os.getcwd()
    print(cwd)

    for file in file_paths:
        markdown_text = process_file(file)

        new_path = file.replace(".csv", ".md").replace("/preprocessors/", "/docs/")

        with open(new_path, "w", encoding="utf-8") as f:
            f.write(markdown_text)

import csv
import os

def reformat_ingredients_csv(input_file, output_file):
    """
    Reformat ingredients CSV from original format to edited format.
    
    Original formats: 
    - Black: Components, Sub assemblies, sub-sub assemblies, quantity, wastage, unit, , unit cost, total cost
    - Gold: Component, Sub-assemblies, quantity, wastage, unit, , unit cost, total cost
    
    Target format: Components, Parent-component, Intermediate-component, quantity, wastage, unit, , unit cost, total cost
    
    Logic:
    - If Components column has data: it's a top-level component (no parent)
    - If Sub assemblies column has data: Components becomes parent-component
    - If sub-sub assemblies column has data: Sub assemblies becomes parent-component, Components becomes intermediate-component
    """
    
    with open(input_file, 'r', newline='', encoding='utf-8-sig') as infile:
        reader = csv.reader(infile)
        
        # Read header and modify column names
        header = next(reader)
        
        # Normalize header to match target format
        if len(header) >= 1:
            header[0] = 'Components'  # Standardize first column name
        if len(header) >= 2:
            header[1] = 'Parent-component'  # Second column becomes Parent-component
        if len(header) >= 3 and header[2] not in ['quantity', 'wastage']:
            header[2] = 'Intermediate-component'  # Third column if it exists and isn't quantity
        elif len(header) >= 3 and header[2] in ['quantity', 'wastage']:
            # Gold format - insert Intermediate-component column
            header.insert(2, 'Intermediate-component')
        
        rows = []
        current_main_component = None
        current_sub_component = None
        
        for row in reader:
            if len(row) < 2:
                continue
                
            # Handle different file structures
            component = row[0].strip() if row[0] else ""
            sub_assembly = row[1].strip() if len(row) > 1 and row[1] else ""
            
            # For files with sub-sub assemblies (Black format)
            sub_sub_assembly = ""
            if len(row) > 2 and row[2] and row[2].strip() and row[2] not in ['quantity', 'wastage'] and not row[2].replace('.', '').isdigit():
                sub_sub_assembly = row[2].strip()
            
            # Skip empty rows
            if not component and not sub_assembly and not sub_sub_assembly:
                continue
            
            new_row = row[:]  # Copy the original row
            
            # Ensure new_row has enough columns for target format
            while len(new_row) < len(header):
                new_row.append("")
            
            if component and not sub_assembly and not sub_sub_assembly:
                # Top-level component - no parent or intermediate
                current_main_component = component
                new_row[1] = ""  # No parent-component
                new_row[2] = ""  # No intermediate-component
                
            elif not component and sub_assembly and not sub_sub_assembly:
                # Sub-assembly ingredient - parent is the current main component
                new_row[0] = sub_assembly  # Move to Components column
                new_row[1] = current_main_component if current_main_component else ""  # Parent-component
                new_row[2] = ""  # No intermediate-component
                current_sub_component = sub_assembly
                
            elif not component and not sub_assembly and sub_sub_assembly:
                # Sub-sub-assembly ingredient - has both parent and intermediate
                new_row[0] = sub_sub_assembly  # Move to Components column
                new_row[1] = current_main_component if current_main_component else ""  # Parent-component
                new_row[2] = current_sub_component if current_sub_component else ""  # Intermediate-component
                
            # Adjust row length to match header
            new_row = new_row[:len(header)]
            while len(new_row) < len(header):
                new_row.append("")
                
            rows.append(new_row)
    
    # Write the reformatted data
    with open(output_file, 'w', newline='', encoding='utf-8') as outfile:
        writer = csv.writer(outfile)
        writer.writerow(header)
        writer.writerows(rows)

def main():
    # Process Black ingredients
    black_input = "Black-ingredients.csv"
    black_output = "Black-ingredients-edited.csv"
    
    # Process Gold ingredients
    gold_input = "Gold-ingredients.csv"
    gold_output = "Gold-ingredients-edited.csv"
    
    files_to_process = [
        (black_input, black_output),
        (gold_input, gold_output)
    ]
    
    for input_file, output_file in files_to_process:
        if os.path.exists(input_file):
            print(f"Processing {input_file} -> {output_file}")
            reformat_ingredients_csv(input_file, output_file)
            print(f"Successfully created {output_file}")
        else:
            print(f"Warning: {input_file} not found")
    
    print("Reformatting complete!")

if __name__ == "__main__":
    main()
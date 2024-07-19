import streamlit as st
import pandas as pd
import io
import nltk
import csv
import re,syllapy
import pycountry


st.set_page_config(page_title="AIO Truncation App")

col1,col2,col3=st.columns(3)
with col2:
    st.image('logo.png',width=300)


st.title("Upload a file for truncation 📑")

uploaded_file = st.file_uploader("Choose an Excel file", type="xlsx")


nltk.download('wordnet')
from nltk.stem import WordNetLemmatizer
lemmatizer = WordNetLemmatizer()


def remove_special_chars(s):
    return re.sub('[^a-zA-Z0-9/$]', ' ', s)


def check_multi_syllable(word):
    num_syllables = syllapy.count(word)
    return num_syllables


def remove_inner_vowels(s):
    if len(s) <= 2:  # If the string is two characters or less, return it as is
        return s
    vowels = "aeiouAEIOU"
    # Keep the first and last character as is, and remove vowels from the rest
    return s[0] + ''.join([char for char in s[1:-1] if char not in vowels]) + s[-1]

def clean_string(s):
    # Remove numbers
    s = re.sub(r'\d+', '', s)
    
    # Remove words starting with a number
    s = re.sub(r'\b\d\w*', '', s)
    
    # Remove units like oz and lb
    s = re.sub(r'\boz\b|\blb\b', '', s)
    
    # Remove extra spaces
    s = ' '.join(s.split())

    s=s.replace("and ","&")

    for country in pycountry.countries:
        # Check if the country's name is in the sentence
        if country.name.lower() in s:
            s=s.replace(country.name.lower(),'')
    
    return s



def remove_descriptions(sentence):
    sentence=sentence.lower().split("with")[0] 
    sentence=sentence.lower().split("choice")[0]
    sentence=clean_string(sentence)
    return sentence


def start_truncation(file_name):
    category_data=pd.read_excel(file_name,sheet_name="Category")
    category_items=pd.read_excel(file_name,sheet_name="Category Items")
    item_data=pd.read_excel(file_name,sheet_name="Item")
    truncation_dict=pd.read_excel('Truncation Dictionary.xlsx',sheet_name=['WINE','COFFEE','BEER','COCKTAIL','LIQOUR'])

    items_trunction_dict={}
    for key,value in truncation_dict.items():
        for i in range(len(value['Actual'])):
            items_trunction_dict[str(value['Actual'].loc[i]).lower()]=str(value['Short Name'].loc[i]).lower()


    items_dict={}
    for id,name in zip(item_data['id'],item_data['itemName']):
        items_dict[id]=[str(name)]

    for key in items_dict:
        link=category_items[category_items['id']==key]['categoryId']
        link_category=category_data[category_data['id']==link.values[0]]['categoryName']
        
        items_dict[key].append(str(link_category.values[0]))

    new_dict={}


    for key,value in items_dict.items():
        N_value=[]
        new_value=""
        new_category=""
        for val in value[0].split(" "):
            verb_root = lemmatizer.lemmatize(val.lower(), pos='v')
            noun_root = lemmatizer.lemmatize(verb_root, pos='n')
            new_value+=noun_root+" " 
        
        for val in value[1].split(" "):
            verb_root = lemmatizer.lemmatize(val.lower(), pos='v')
            noun_root = lemmatizer.lemmatize(verb_root, pos='n')
            new_category+=noun_root+" " 
        if value[0]==value[1]:
            continue
        splitted_category=new_category.split(" ")
        for splitted in splitted_category:
            if splitted in new_value:
                new_value=new_value.replace(splitted,"")
        new_value = remove_special_chars(new_value).replace("  "," ")
        new_dict[key]=[value[1],new_value.capitalize().strip()]

    for key,value in new_dict.items():
        new_word=""
        values=value[1].split()
        for splitted in values:
            if splitted.lower().strip() in items_trunction_dict:
                new_word+=items_trunction_dict[splitted.lower().strip()]+" "
            else:
                new_word+=splitted+" "
        value[1]=new_word.strip()

    
    for key,value in new_dict.items():
        if len(value[1])>16:
            new_word=""
            values=remove_descriptions(value[1]).split()
            for splitted in values:
                dict_values = items_trunction_dict.values()
                if splitted.lower().strip() not in list(dict_values):
                    if check_multi_syllable(splitted.strip())>1:
                        new_word+=remove_inner_vowels(splitted.strip())+" "
                    else:
                        new_word+=splitted+" "
                else:
                    new_word+=splitted+" "
            value[1]=new_word

    actual=[]
    for key,value in items_dict.items():
        actual.append(value[0])
    rows=[]
    i=0
    for key,value in new_dict.items():
        if len(actual[i])<=16:
            rows.append([value[0],actual[i],actual[i],len(actual[i])])
        else:
            
            rows.append([value[0],actual[i],value[1],len(value[1])])
        i+=1

    return rows

if uploaded_file is not None:
    try:
        rows=start_truncation(uploaded_file)
        df = pd.DataFrame(rows,columns=["Category","Actual","Truncated","truncated length"])

        # Save the DataFrame to an Excel file in memory
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='truncation sheet')

        # Seek to the beginning of the stream
        output.seek(0)

        # Streamlit code to provide the download link
        st.title('Download Truncated File')
        st.download_button(
            label="Download🗃️",
            data=output,
            file_name='output.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        st.write("Error Occured: ",e)
    
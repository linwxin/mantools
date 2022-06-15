import json
import os

import pandas as pd

def resolve_json(json_str):
    origin = json.loads(json_str)
    if "sort_count" not in origin.keys():
        return dict()
    sort_count = origin["sort_count"]
    result = dict()
    result["doi"] = origin["identifier"]["doi"][0]["value"]
    for k1, v1 in sort_count.items():
        result[k1] = dict()
        result[k1]["total"] = v1["total"]
        # 处理count_types
        count_types = v1["count_types"]
        for e in count_types:
            temp = dict()
            sources = e["sources"]
            for s in sources:
                if s["name"] in temp.keys():
                    temp[s["name"]] += s["total"]
                else:
                    temp[s["name"]] = s["total"]
            temp_total = 0
            for c_k, c_v in temp.items():
                temp_total += c_v
            if e["name"] == "CITED_BY_COUNT":
                temp["total"] = e["total"]
            else:
                temp["total"] = temp_total
            result[k1][e["name"]] = dict(temp)

    return result

def merge_to_one_dict(d_l):
    result = dict()
    for line in d_l:
        tmp = dict()
        for k, v in line.items():
            if k != "doi":
                tmp[k] = v
        result[line["doi"]] = dict(tmp)
    print(result)
    return result

# 将键值对结构调整一致, 最多四层
def reset_dict(ds, path):
    col_names = set()
    # 第1层
    F1 = ["usage", "capture", "citation", "social_media", "mention"]
    # 获取标题集合
    for d in ds:
        for f1 in F1:
            if f1 not in d.keys():
                continue
            for k2, v2 in d[f1].items():
                tmp_col_name = f1
                tmp = d[f1]
                if isinstance(tmp[k2], dict):
                    tmp_col_name += "-" + k2
                    for k3, v3 in tmp[k2].items():
                        if f1 == "social_media" and k3 == "total":
                            continue
                        col_names.add(tmp_col_name + "-" + k3)
                else:
                    tmp_col_name += "-" + k2
                    col_names.add(tmp_col_name)
    print(col_names)
    # 生成list
    col_names = sorted(list(col_names))
    col_names.insert(0, "doi")
    col_names.insert(0, "paper_title")
    data = list()
    for d in ds:
        line = []
        for col_name in col_names:
            if len(col_name.split("-")) == 2:
                col_keys = col_name.split("-")
                try:
                    line.append(d[col_keys[0]][col_keys[1]])
                except:
                    line.append(0)
            elif len(col_name.split("-")) == 3:
                col_keys = col_name.split("-")
                try:
                    line.append(d[col_keys[0]][col_keys[1]][col_keys[2]])
                except:
                    line.append(0)
            elif len(col_name.split("-")) == 1:
                col_keys = col_name.split("-")
                try:
                    line.append(d[col_keys[0]])
                except:
                    line.append("")
            elif len(col_name.split("-")) == 4:
                col_keys = col_name.split("-")
                try:
                    line.append(d[col_keys[0]][col_keys[1]][col_keys[2]][col_keys[3]])
                except:
                    line.append(0)
        data.append(line)
    print(data)
    save_dict_to_csv(data, col_names, path)

    return data

def save_dict_to_csv(data, col_names, path):
    df = pd.DataFrame(data, columns=col_names)
    df.to_csv(path, index=False)


def merge_scopus_with_spider_data(f1, f2):

    pass



def merge_plumx_test():
    test_case = [
        {'doi': '10.1038/nature14236', 'usage': {'total': 7233, 'ABSTRACT_VIEWS': {'EBSCO': 4522, 'total': 4522},
                                                 'FULL_TEXT_VIEWS': {'EBSCO': 1629, 'total': 1629},
                                                 'LINK_CLICK_COUNT': {'Bitly': 769, 'total': 769},
                                                 'LINK_OUTS': {'EBSCO': 313, 'total': 313}},
         'capture': {'total': 828, 'READER_COUNT': {'Mendeley': 642, 'CiteULike': 31, 'total': 673},
                     'EXPORTS_SAVES': {'EBSCO': 155, 'total': 155}}, 'citation': {'total': 8523,
                                                                                  'CITED_BY_COUNT': {'Scopus': 8470,
                                                                                                     'CrossRef': 5671,
                                                                                                     'PubMed': 456,
                                                                                                     'total': 14597},
                                                                                  'PATENT_FAMILY_COUNT': {
                                                                                      'Patent Families': 53,
                                                                                      'total': 53}},
         'social_media': {'total': 1286, 'TWEET_COUNT': {'Twitter': 695, 'total': 695},
                          'FACEBOOK_COUNT': {'Facebook': 591, 'total': 591}},
         'mention': {'total': 175, 'COMMENT_COUNT': {'Reddit': 71, 'total': 71},
                     'ALL_BLOG_COUNT': {'Blog': 54, 'total': 54}, 'NEWS_COUNT': {'News': 22, 'total': 22},
                     'QA_SITE_MENTIONS': {'Stack Exchange': 17, 'total': 17},
                     'REFERENCE_COUNT': {'Wikipedia': 11, 'total': 11}},
         'paper_title': 'Human-level control through deep reinforcement learning'},
        {'doi': '10.1038/nature14133', 'usage': {'total': 3606, 'FULL_TEXT_VIEWS': {'EBSCO': 2367, 'total': 2367},
                                                 'ABSTRACT_VIEWS': {'EBSCO': 1197, 'total': 1197},
                                                 'LINK_OUTS': {'EBSCO': 39, 'total': 39},
                                                 'LINK_CLICK_COUNT': {'Bitly': 3, 'total': 3}},
         'capture': {'total': 2646, 'READER_COUNT': {'Mendeley': 2636, 'total': 2636},
                     'EXPORTS_SAVES': {'EBSCO': 10, 'total': 10}},
         'citation': {'total': 4201, 'CITED_BY_COUNT': {'Scopus': 4189, 'CrossRef': 3055, 'PubMed': 27, 'total': 7271},
                      'PATENT_FAMILY_COUNT': {'Patent Families': 12, 'total': 12}},
         'social_media': {'total': 31, 'FACEBOOK_COUNT': {'Facebook': 19, 'total': 19},
                          'TWEET_COUNT': {'Twitter': 12, 'total': 12}},
         'mention': {'total': 1, 'NEWS_COUNT': {'News': 1, 'total': 1}},
         'paper_title': 'Compositional engineering of perovskite materials for high-performance solar cells'},
        {'doi': '10.1038/nature14248', 'usage': {'total': 6947, 'ABSTRACT_VIEWS': {'EBSCO': 6670, 'total': 6670},
                                                 'FULL_TEXT_VIEWS': {'EBSCO': 233, 'total': 233},
                                                 'LINK_CLICK_COUNT': {'Bitly': 39, 'total': 39},
                                                 'LINK_OUTS': {'EBSCO': 5, 'total': 5}},
         'capture': {'total': 3730, 'READER_COUNT': {'Mendeley': 3696, 'CiteULike': 21, 'total': 3717},
                     'EXPORTS_SAVES': {'EBSCO': 13, 'total': 13}}, 'citation': {'total': 3031,
                                                                                'CITED_BY_COUNT': {'CrossRef': 3023,
                                                                                                   'Scopus': 2863,
                                                                                                   'PubMed': 2227,
                                                                                                   'total': 8113},
                                                                                'PATENT_FAMILY_COUNT': {
                                                                                    'Patent Families': 8, 'total': 8}},
         'social_media': {'total': 678, 'FACEBOOK_COUNT': {'Facebook': 630, 'total': 630},
                          'TWEET_COUNT': {'Twitter': 48, 'total': 48}},
         'mention': {'total': 47, 'REFERENCE_COUNT': {'Wikipedia': 32, 'total': 32},
                     'NEWS_COUNT': {'News': 14, 'total': 14}, 'ALL_BLOG_COUNT': {'Blog': 1, 'total': 1}},
         'paper_title': 'Integrative analysis of 111 reference human epigenomes'},
        {'doi': '10.1038/nature13774', 'usage': {'total': 1361, 'ABSTRACT_VIEWS': {'EBSCO': 1092, 'total': 1092},
                                                 'FULL_TEXT_VIEWS': {'EBSCO': 236, 'total': 236},
                                                 'LINK_OUTS': {'EBSCO': 33, 'total': 33}},
         'capture': {'total': 924, 'READER_COUNT': {'Mendeley': 889, 'CiteULike': 1, 'total': 890},
                     'EXPORTS_SAVES': {'EBSCO': 34, 'total': 34}}, 'citation': {'total': 2537,
                                                                                'CITED_BY_COUNT': {'Scopus': 2537,
                                                                                                   'CrossRef': 1445,
                                                                                                   'PubMed': 192,
                                                                                                   'total': 4174}},
         'social_media': {'total': 17, 'TWEET_COUNT': {'Twitter': 15, 'total': 15},
                          'FACEBOOK_COUNT': {'Facebook': 2, 'total': 2}},
         'mention': {'total': 2, 'REFERENCE_COUNT': {'Wikipedia': 1, 'total': 1},
                     'NEWS_COUNT': {'News': 1, 'total': 1}},
         'paper_title': 'High secondary aerosol contribution to particulate pollution during haze events in China'},
        {'doi': '10.1038/nature15371', 'usage': {'total': 5802, 'ABSTRACT_VIEWS': {'EBSCO': 3967, 'total': 3967},
                                                 'FULL_TEXT_VIEWS': {'EBSCO': 1647, 'total': 1647},
                                                 'LINK_OUTS': {'EBSCO': 185, 'total': 185},
                                                 'LINK_CLICK_COUNT': {'Bitly': 3, 'total': 3}},
         'capture': {'total': 2590, 'READER_COUNT': {'Mendeley': 2397, 'CiteULike': 4, 'total': 2401},
                     'EXPORTS_SAVES': {'EBSCO': 189, 'total': 189}}, 'citation': {'total': 2361,
                                                                                  'CITED_BY_COUNT': {'Scopus': 2360,
                                                                                                     'CrossRef': 1241,
                                                                                                     'PubMed': 417,
                                                                                                     'Academic Citation Index (ACI) - airiti': 2,
                                                                                                     'total': 4020},
                                                                                  'POLICY_CITED_BY_COUNT': {
                                                                                      'Policy Citation': 1,
                                                                                      'total': 1}},
         'social_media': {'total': 1242, 'FACEBOOK_COUNT': {'Facebook': 824, 'total': 824},
                          'TWEET_COUNT': {'Twitter': 418, 'total': 418}},
         'mention': {'total': 71, 'NEWS_COUNT': {'News': 40, 'total': 40}, 'ALL_BLOG_COUNT': {'Blog': 16, 'total': 16},
                     'REFERENCE_COUNT': {'Wikipedia': 6, 'total': 6}, 'COMMENT_COUNT': {'Reddit': 5, 'total': 5},
                     'QA_SITE_MENTIONS': {'Stack Exchange': 3, 'total': 3}, 'LINK_COUNT': {'Wikipedia': 1, 'total': 1}},
         'paper_title': 'The contribution of outdoor air pollution sources to premature mortality on a global scale'},
        {'doi': '10.1038/nature13970', 'usage': {'total': 1322, 'ABSTRACT_VIEWS': {'EBSCO': 1111, 'total': 1111},
                                                 'FULL_TEXT_VIEWS': {'EBSCO': 197, 'total': 197},
                                                 'LINK_OUTS': {'EBSCO': 14, 'total': 14}},
         'capture': {'total': 1175, 'READER_COUNT': {'Mendeley': 1151, 'CiteULike': 1, 'total': 1152},
                     'EXPORTS_SAVES': {'EBSCO': 23, 'total': 23}},
         'citation': {'total': 2177, 'CITED_BY_COUNT': {'Scopus': 2176, 'CrossRef': 1160, 'PubMed': 5, 'total': 3341},
                      'PATENT_FAMILY_COUNT': {'Patent Families': 1, 'total': 1}},
         'social_media': {'total': 11, 'TWEET_COUNT': {'Twitter': 10, 'total': 10},
                          'FACEBOOK_COUNT': {'Facebook': 1, 'total': 1}},
         'mention': {'total': 2, 'REFERENCE_COUNT': {'Wikipedia': 1, 'total': 1},
                     'NEWS_COUNT': {'News': 1, 'total': 1}},
         'paper_title': "Conductive two-dimensional titanium carbide 'clay' with high volumetric capacitance"}
    ]
    reset_dict(test_case)


"""
合并所有scopus文件
"""
def merge_scopus(scopus, useful_col):
    dfs = []
    print(scopus)
    for s in scopus:
        try:
            df = pd.read_csv(s, encoding="utf-8")
        except:
            print("出问题的scopus:" + s)
            df = pd.read_csv(s, encoding="gbk")
        df = df.loc[:, useful_col]
        dfs.append(df)
    return pd.concat(dfs)




if __name__ == "__main__":

    scopus = []
    # for nap in ["./science-ar", "./science-ex-ar-no", "./science-no"]:
    for nap in ["./nature-ar", "./nature-ar-exclude-human", "./nature-ar-human", "./nature-exclude-ar"]:
        years = os.listdir(nap)
        for y in years:
            scopus.append(os.path.join(nap, y, "scopus.csv"))
    print(scopus)
    cols = []
    with open("./resource/csv_needed.txt", encoding="utf-8") as f:
        for line in f.readlines():
            cols.append(line.strip().replace("\n", ""))
    res = merge_scopus(scopus, cols)
    res.to_csv("./resource/nature_scopus.csv", index=False)
    # df1 = pd.read_csv("./nature-exclude-ar/21206_2016/scopus-limit-human.csv")
    # df2 = pd.read_csv("./nature-exclude-ar/21206_2016/scopus-exclude-human.csv")
    # df3 = pd.concat([df1, df2])
    # df3.to_csv("./nature-exclude-ar/21206_2016/scopus.csv", index=False)
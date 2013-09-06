import os
import sequence_serializer
import component_union
import random
import modeling
import modeling2
import database
from math import log10

prom_name = "BBa_I712074"
rbs_name = "BBa_J61104"
term_name = "BBa_B0013"


data = {
    "part": [
      { "id"  : 1,
        "name": "BBa_C0060",
        "type": "Protein"
        },
      { "id"  : 2,
        "name": "repressor",
        "type": "Repressor"
        },
      { "id"  : 3,
        "name": "BBa_C0160",
        "type": "Protein"
        },
      { "id"  : 4,
        "name": "BBa_C0178",
        "type": "Protein"
        }

      ],
    "link": [
      { "from": 1,
        "to"  : 2,
        "type": "Bound",
        },
      { "from": 2,
        "to"  : 3,
        "type": "Repressor",
        "inducer": "Positive"
        },
      { "from": 2,
        "to"  : 4,
        "type": "Repressor",
        "inducer": "Positive"
        },

      ]
}

def find_repressor(item, repressor_list, database):
  if item[3] == "repressor":
    item[3] = database.select_row("repressor", len(repressor_list) + 1)
    repressor_list += item[3]
  if item[-2] == "repressor":
    item[-2] = database.select_row("repressor", len(repressor_list) + 1)
    repressor_list += item[-2]
  return item

def find_activator(item, activator_list, database):
  if item[3] == "activator":
    item[3] = database.select_row("activator", len(activator_list) + 1)
    activator_list += item[3]
  if item[-2] == "activator":
    item[-2] = database.select_row("activator", len(activator_list) + 1)
    activator_list += item[-2]
  return item

def find_promoter(database, activator = None, repressor = None):
  if activator is not None:
    return database.find_promoter_with_activator(activator)
  else:
    return database.find_promoter_with_repressor(repressor)

def find_file(name, path):
    for root, dirs, files in os.walk(path):
        if name in files:
            return os.path.join(root, name)


def pre_work(part):
  return [prom_name, rbs_name, part["name"], term_name]

def bind(protein1, protein2):
  return [prom_name, rbs_name, protein1, rbs_name, protein2, term_name]

def activate(database, from_part, to_part):
  ret = to_part
  ret[0] = find_promoter(database, activator = from_part[-2])
  return ret

def repress(database, from_part, to_part):
  ret = to_part
  ret[0] = find_promoter(database, repressor = from_part[-2])
  return ret


def work(data, database):
  groups = {}
  part_list = {}
  bound_list = {}
  rev_bound_list = {}
  repressor_list = []
  activator_list = []
  for part in data["part"]:
    groups[part["id"]] = pre_work(part)
    part_list[part["id"]] = part["name"]

  # combine bound link
  for link in data["link"]:
    if link["type"] == "Bound":
      groups[link["to"]] = bind(part_list[link["from"]], part_list[link["to"]])
      bound_list[link["from"]] = link["to"]
      rev_bound_list[link["to"]] = link["from"]
      for l2 in data["link"]:
        if l2["to"] == link["from"]:
          l2["to"] = link["to"]
      del groups[link["from"]]

  # replace repressor with exact component
  for elem in groups:
    groups[elem] = find_repressor(groups[elem], repressor_list, database)
    groups[elem] = find_activator(groups[elem], repressor_list, database)
  for link in data["link"]:
    # TODO: inducer
    if link["from"] not in groups:
      link["from"] = bound_list[link["from"]]
    if link["to"] not in groups:
      link["to"] = bound_list[link["to"]]

    if link["type"] == "Repressor":
      groups[link["to"]] = repress(database, groups[link["from"]], groups[link["to"]])
    if link["type"] == "Activator":
      groups[link["to"]] = activate(database, groups[link["from"]], groups[link["to"]])
  return (groups, repressor_list, activator_list, rev_bound_list)

def get_start_pos(groups):
  start_pos = []
  for i in groups:
    if groups[i]["from"] == -1:
      start_pos.append(i)
  return start_pos

def dump_sbol(network, database):
  data, r_list, a_list = work(network, database)
  sbol = []
  rule = "RFC10"
  for i in data:
    data[i] = [find_file(s + ".xml", ".") for s in data[i]]
    content = component_union.union(rule, data[i])
    dna_sequence = component_union.connect(rule, content)
    sbol.append(sequence_serializer.format_to_json(component_union.formatter_v11(content, dna_sequence)))
  return sbol

def get_pro_info(database, protein_idx, group, grp_id, backbone = "pSB1AT3"):
  # TODO add pro_type here, merge pro_name here, indexed by pro_id instead.
  ret = {}
  ret["grp_id"] = grp_id
  ret["name"] = group[protein_idx]
  promoter_info= database.select_with_name("promoter", group[0])
  rbs_info= database.select_with_name("RBS", group[protein_idx - 1])
  plasmid_backbone_info = database.select_with_name("plasmid_backbone", backbone)
  ret["PoPS"] = promoter_info["MPPromoter"] * 100
  ret["RIPS"] = rbs_info["MPRBS"] * 100
  ret["copy"] = plasmid_backbone_info["CopyNumber"]
  ret["repress_rate"] = -1
  ret["induce_rate"] = -1
  ret["concen"] = 0.1
  # following arguments are DEPRECATED
  return ret

def get_index_in_group(pro_name, group):
  for i in range(len(group)):
    if group[i]["name"] == pro_name:
      return i

def update_proteins_repress(database, protein, groups):
  start_pos = get_start_pos(groups)
  for st in start_pos:
    origin_concen = modeling2.SteadyState_Concen(database, protein, groups, st)
    actrep_concen = modeling2.SteadyState_Concen_ActRep(database, protein,\
        groups, st)
    corepind_concen = modeling2.SteadyState_Concen_CorepInd(database, protein,\
        groups, {}, st)
    for i in origin_concen:
      protein[i]["repress_rate"] = log10(actrep_concen[i]) - log10(origin_concen[i])
      protein[i]["induce_rate"] = log10(corepind_concen[i]) - log10(origin_concen[i])
      protein[i]["concen"] = actrep_concen[i]

def get_graph(link):
  ret = {}
  for item in link:
    if item["type"] != "Bound":
      ret[item["to"]] = item["from"]
  return ret

def get_graph_type(link):
  link_type = {}
  inducer_type = {}
  for item in link:
    if item["type"] == "Bound":
      continue
    if item["type"] == "Repressor":
      link_type[item["to"]] = "Negative"
    elif item["type"] == "Activator":
      link_type[item["to"]] = "Positive"
    inducer_type[item["to"]] = item["inducer"]
  return link_type, inducer_type

def dump_group(network, database):
  graph = get_graph(network["link"])
  link_type, inducer_type = get_graph_type(network["link"])
  data, r_list, a_list, b_list = work(network, database)
  groups = {}
  proteins = {}
  plasmid = []
  for i in data:
    # proteins[data[i][2]] = get_pro_info(database, 2, data[i], i)
    proteins[i] = get_pro_info(database, -2, data[i], i)
    if len(data[i]) == 6:
      # proteins[data[i][4]] = get_pro_info(database, 4, data[i], i)
      proteins[b_list[i]] = get_pro_info(database, 2, data[i], i)
    grp = []
    for elem in data[i]:
      xml_file = find_file(elem + ".xml", ".")
      grp.append({"name": elem, "type": component_union.get_rule(xml_file)})
    grp[-2]["id"] = i
    if len(data[i]) == 6:
      grp[2]["id"] = b_list[i]
    if i in graph:
      prev = graph[i]
    else:
      prev = -1
    if prev == -1:
      g_type = "Constitutive"
      i_type = "None"
    else:
      g_type = link_type[i]
      i_type = inducer_type[i]

    # plasmids.append({"id": i, "sbol":grp, "state": "cis", "from": prev})
    groups[i] = {"sbol":grp, "state": "cis", "type": g_type, "inducer": i_type, "from": prev, "to": []}
    plasmid.append(i)
  for i in graph:
    groups[graph[i]]["to"].append(i)
  update_proteins_repress(database, proteins, groups)
  return {"groups": groups, "proteins": proteins, "plasmids": [plasmid]}

'''	sbol_dict is the sbol create by this python program
	rbs_value is the new value that user want for the rbs
	proteinName is the protein that the user want to change
'''
def changeRBS_MPRBS(database,sbol_dict,rbs_value,proteinName):
  bestRBS= database.getRBSNearValue(rbs_value)
  for item in sbol_dict:
    for i in range(0,len(item)):
      if item[i]['name']==proteinName:
        if item[i-1]['type']=='RBS':
          item[i-1]['name']=bestRBS['Number']
  return sbol_dict

def get_type_of_promoter(p_type):
  if p_type == "Constitutive":
    return "PoPS"
  elif p_type == "Negative":
    return "MPPromoter"
  elif p_type == "Positive":
    return "LeakageRate"

def js_formatter(gene_circuit):
  new_proteins = {}
  for i in gene_circuit["proteins"]:
    new_proteins[int(i)] = gene_circuit["proteins"][i]
  gene_circuit["proteins"] = new_proteins
  new_groups = {}
  for i in gene_circuit["groups"]:
    new_groups[int(i)] = gene_circuit["groups"][i]
  gene_circuit["groups"] = new_groups
  return gene_circuit


def update_controller(db, update_info):
  gene_circuit = js_formatter(update_info["gene_circuit"])
  detail = update_info["detail"]
  pro_id = detail["pro_id"]
  protein = gene_circuit["proteins"][pro_id]
  pro_name = protein["name"]
  grp_id = protein["grp_id"]
  group = gene_circuit["groups"][grp_id]

  if detail["type"] == "RIPS":
    rbs_value = float(detail["new_value"]) / 100
    idx = get_index_in_group(pro_name, group["sbol"])
    bestRBS = db.getRBSNearValue(rbs_value)
    gene_circuit["groups"][grp_id]["sbol"][idx-1]["name"] = bestRBS["Number"]
    gene_circuit["proteins"][pro_id]["RIPS"] = bestRBS["MPRBS"] * 100

  elif detail["type"] == "copy":
    for plasmid in gene_circuit["plasmids"]:
      for item in plasmid:
        if item == grp_id:
          updated_plasmid = plasmid
          break
    copy_value = detail["new_value"]
    for i in gene_circuit["proteins"]:
      if gene_circuit["proteins"][i]["grp_id"] in updated_plasmid:
        gene_circuit["proteins"][i]["copy"] = copy_value

  elif detail["type"] == "PoPS":
    prev_grp = group["from"]
    promoter_value = float(detail["new_value"]) / 100
    try:
      repressor_list = detail["repressor_list"]
    except:
      repressor_list = []
    try:
      activator_list = detail["activator_list"]
    except:
      activator_list = []
    link_type = group["type"]
    p_type = get_type_of_promoter(link_type)
    best_promoter = db.getPromoterNearValue(promoter_value, repressor_list,\
        link_type, p_type)
    gene_circuit["groups"][grp_id]["sbol"][0]["name"] = best_promoter["Number"]
    pro1_id = gene_circuit["groups"][grp_id]["sbol"][2]["id"]
    pro2_id = gene_circuit["groups"][grp_id]["sbol"][-2]["id"]
    gene_circuit["proteins"][pro1_id]["PoPS"] = best_promoter[p_type] * 100
    gene_circuit["proteins"][pro2_id]["PoPS"] = best_promoter[p_type] * 100
    if prev_grp != -1:
      repressor_id = gene_circuit["groups"][prev_grp]["sbol"][-2]["id"]
      new_repressor = db.find_repressor_with_promoter(best_promoter["Number"])
      gene_circuit["proteins"][repressor_id]["name"] = new_repressor
      gene_circuit["groups"][prev_grp]["sbol"][-2]["name"] = new_repressor

  elif detail["type"] == "K1":
    #TODO not completed yet!!!

    # update promoter related to repressor
    best_promoter = db.find_promoter_with_repressor(best_repressor["Number"])
    promoter_value = (db.select_with_name("promoter",\
      best_promoter))["MPPromoter"]
    for next_grp in group["to"]:
      promoter_grp = gene_circuit["proteins"][i]["grp_id"]
      gene_circuit["proteins"]
      gene_circuit["proteins"][i]["PoPS"] = promoter_value
      gene_circuit["groups"][promoter_grp][0]["name"] = best_promoter

  update_proteins_repress(db, gene_circuit["proteins"],\
      gene_circuit["groups"])
  print gene_circuit
  return gene_circuit

if __name__ == "__main__":
  db = database.SqliteDatabase()
  #sbol=dump_group(data, db)
  #print sbol
  update_info = {u'detail': {u'repressor_list': [], u'new_value': 78, u'type':
    u'RIPS', u'pro_id': 1}, u'gene_circuit': {u'proteins': {u'1': {u'RIPS': 11, u'name': u'BBa_C0060', u'concen': 8, u'grp_id': 2, u'PoPs': 78, u'before_regulated': 20, u'K1': 3, u'induce_rate': 30, u'copy': 73, u'after_regulated': 100}, u'3': {u'RIPS': 11, u'name': u'BBa_C0160', u'concen': 100, u'grp_id': 3, u'PoPs': 56, u'before_regulated': 0, u'K1': 3, u'induce_rate': 0, u'copy': 73, u'after_regulated': 0}, u'2': {u'RIPS': 11, u'name': u'BBa_K518003', u'concen': 8, u'grp_id': 2, u'PoPs': 95, u'before_regulated': 0, u'K1': 3, u'induce_rate': 0, u'copy': 73, u'after_regulated': 100}, u'4': {u'RIPS': 11, u'name': u'BBa_C0178', u'concen': 100, u'grp_id': 4, u'PoPs': 56, u'before_regulated': 0, u'K1': 3, u'induce_rate': 0, u'copy': 73, u'after_regulated': 0}}, u'plasmids': [[2, 3, 4]], u'groups': {u'3': {u'to':[], u'sbol': [{u'type': u'Regulatory', u'name': u'BBa_J64000'}, {u'type': u'RBS', u'name': u'BBa_J61104'}, {u'type': u'Coding', u'name': u'BBa_C0160', u'id': 3}, {u'type': u'Terminator', u'name': u'BBa_B0013'}], u'from': 2, u'state': u'cis', u'type': u'Negative'}, u'2': {u'to': [3, 4], u'sbol': [{u'type': u'Regulatory', u'name': u'BBa_I712074'}, {u'type': u'RBS', u'name': u'BBa_J61104'}, {u'type': u'Coding', u'name': u'BBa_C0060', u'id': 1}, {u'type': u'RBS', u'name': u'BBa_J61104'}, {u'type': u'Coding', u'name': u'BBa_K518003', u'id': 2}, {u'type': u'Terminator', u'name': u'BBa_B0013'}], u'from': -1, u'state': u'cis', u'type': u'Constitutive'}, u'4': {u'to': [], u'sbol': [{u'type': u'Regulatory', u'name': u'BBa_J64000'}, {u'type': u'RBS', u'name': u'BBa_J61104'}, {u'type': u'Coding', u'name': u'BBa_C0178', u'id': 4}, {u'type': u'Terminator', u'name': u'BBa_B0013'}],u'from': 2, u'state': u'cis', u'type': u'Negative'}}}}
  update_controller(db, update_info)

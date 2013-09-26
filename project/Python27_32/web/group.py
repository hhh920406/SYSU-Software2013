##
# @file group.py
# @brief generate gene circuit with given regulation network
# @author Jianhong Li
# @version 1.0
# @date 2013-08-31
# @copyright 2013 SYSU-Software. All rights reserved.
# This project is released under MIT License.
#

import os
from sbol2json import format_to_json
import component_union
import SteadyState_Rate
import random
import database
from math import log10

prom_name = "BBa_I712074"
rbs_name = "BBa_J61104"
term_name = "BBa_B0013"

# --------------------------------------------------------------------------
##
# @brief find a unique repressor
#
# @param database  database instance
# @param item      repressor
# @param regulator_list currently used repressor and activator
#
# @returns   selected repressor
#
# --------------------------------------------------------------------------
def find_repressor(database, item, regulator_list):
  item = database.select_row("repressor", len(regulator_list) + 1)
  regulator_list += item
  return str(item)

# --------------------------------------------------------------------------
##
# @brief find a unique activator
#
# @param database        database instance
# @param item            activator
# @param regulator_list  currently used repressor and activator
#
# @returns   select activator
#
# --------------------------------------------------------------------------
def find_activator(database, item, regulator_list):
  item = database.select_row("activator", len(regulator_list) + 1)
  regulator_list += item
  return str(item)

# --------------------------------------------------------------------------
##
# @brief find a promoter corresponding to regulator
#
# @param db         database instance
# @param activator  optional activator
# @param repressor  optional repressor
#
# @returns   selected promoter
#
# --------------------------------------------------------------------------
def find_promoter(db, activator = None, repressor = None):
  if activator is not None:
    return db.find_promoter_with_activator(activator)
  else:
    return db.find_promoter_with_repressor(repressor)

# --------------------------------------------------------------------------
##
# @brief find a file with given file name and path
#
# @param name  file name
# @param path  file path
#
# @returns     the file with path
#
# --------------------------------------------------------------------------
def find_file(name, path):
    for root, dirs, files in os.walk(path):
        if name in files:
            return os.path.join(root, name)


# --------------------------------------------------------------------------
##
# @brief get group list with a protein
#
# @param part  protein
#
# @returns   the group list
#
# --------------------------------------------------------------------------
def pre_work(part):
  return [prom_name, rbs_name, part["name"], term_name]

# --------------------------------------------------------------------------
##
# @brief connect two bounded component
#
# @param protein1 the first protein
# @param protein2 the second protein
#
# @returns   connected components
# 
# --------------------------------------------------------------------------
def bind(protein1, protein2):
  l1 = len(protein1) - 1
  l2 = len(protein2) - 1
  return [prom_name] + protein1[1:l1] + protein2[1:l2] + [term_name]

# --------------------------------------------------------------------------
##
# @brief find group name of bounded components using disjoint set
#
# @param v           current node
# @param bound_list  the relation of bound edges
#
# @returns   the group name of bounded components
#
# --------------------------------------------------------------------------
def find_bound_src(v, bound_list):
  if bound_list[v] != v:
    bound_list[v] = find_bound_src(bound_list[v], bound_list)
  return bound_list[v]

# --------------------------------------------------------------------------
##
# @brief generate group list with regulation network
#
# @param data      regulation network
# @param database  databse instance
#
# @returns         group list
#
# --------------------------------------------------------------------------
def work(data, database):
  groups = {}
  part_list = {}
  bound_list = {}
  pro_pos = {}
  rev_bound_list = {}
  regulator_list = []
  # Initialization
  for part in data["part"]:
    idx = part["id"]
    groups[idx] = pre_work(part)
    part_list[idx] = part["name"]
    bound_list[idx] = idx
    pro_pos[idx] = 2

  # combine bound link
  for link in data["link"]:
    if link["type"] == "Bound":
      u = bound_list[link["from"]]
      v = bound_list[link["to"]]
      if u == v:
        continue
      groups[v] = bind(groups[u], groups[v])
      offset = len(groups[u]) - 2
      for p in data["part"]:
        idx = p["id"]
        if bound_list[idx] == v:
          pro_pos[idx] += offset
        if bound_list[idx] == u:
          bound_list[idx] = v
      bound_list[u] = v
      rev_bound_list[v] = u
      del groups[u]

  # replace repressor with exact component
  for elem in groups:
    for i in xrange(len(groups[elem])):
      if groups[elem][i] == "Repressor":
        groups[elem][i] = find_repressor(database, groups[elem][i],\
            regulator_list)
      if groups[elem][i] == "Activator":
        groups[elem][i] = find_activator(database, groups[elem][i],\
            regulator_list)

  for i in bound_list:
    bound_list[i] = find_bound_src(bound_list[i], bound_list)
  for link in data["link"]:
    if link["type"] == "Bound":
      continue
    next_grp = bound_list[link["from"]]
    for p in data["part"]:
      if p["id"] == link["from"]:
        cur = p
        break
    if cur["type"] == "Repressor":
      groups[next_grp][0] = find_promoter(database, repressor=cur["name"])["Number"]
    if cur["type"] == "Activator":
      groups[next_grp][0] = find_promoter(database, activator=cur["name"])["Number"]
  return (groups, bound_list, pro_pos)

# --------------------------------------------------------------------------
##
# @brief get protein info from database
#
# @param database     database instance
# @param protein_idx  the protein index in the group
# @param groups       all groups in gene circuit
# @param grp_id       group id of the protein
# @param regulator    regulator to the protein
# @param backbone     plasmid backbone, pSB1AT3 by default
#
# @returns   protein info
#
# --------------------------------------------------------------------------
def get_pro_info(database, protein_idx, groups, grp_id, regulator, backbone = "pSB1AT3"):
  ret = {}
  cur_group = groups[grp_id]["sbol"]
  link_type = groups[grp_id]["type"]
  if link_type == "Positive":
    regulator_info = database.select_with_name("activator", regulator)
  elif link_type == "Negative":
    regulator_info = database.select_with_name("repressor", regulator)
  else:
    regulator_info = None
  promoter_info= database.select_with_name("promoter", cur_group[0]["name"])
  rbs_info= database.select_with_name("RBS", cur_group[protein_idx - 1]["name"])
  plasmid_backbone_info = database.select_with_name("plasmid_backbone", backbone)
  ret["grp_id"] = grp_id
  ret["name"] = cur_group[protein_idx]["name"]
  ret["PoPS"] = promoter_info[get_type_of_promoter(link_type)]
  ret["RiPS"] = rbs_info["MPRBS"]
  ret["copy"] = plasmid_backbone_info["CopyNumber"]
  if regulator_info is not None:
    ret["K1"] = log10(regulator_info["K1"])
  else:
    ret["K1"] = None
  ret["repress_rate"] = -1
  ret["induce_rate"] = -1
  if groups[grp_id]["corep_ind_type"] == "None":
    ret["concen"] = None
  else:
    ret["concen"] = 0.1

  ret["pos"] = protein_idx
  return ret

def get_index_in_group(pro_name, group):
  for i in range(len(group)):
    if group[i]["name"] == pro_name:
      return i

def update_proteins_repress(database, gene_circuit):
  repress_rates = SteadyState_Rate.ActRepRate(gene_circuit, database)
  induce_rates = SteadyState_Rate.CorepIndRate(gene_circuit, database)
  for i in repress_rates:
    pro = gene_circuit["proteins"][i]
    gene_circuit["proteins"][i]["before_regulated"] =\
        pro["PoPS"] * pro["RiPS"] * pro["copy"]
    gene_circuit["proteins"][i]["repress_rate"] = log10(repress_rates[i])
    gene_circuit["proteins"][i]["induce_rate"] = log10(induce_rates[i])

# --------------------------------------------------------------------------
##
# @brief Get graph without bound edges from link
#
# @param link  links in regulation network
#
# @returns   basic graph info
#
# --------------------------------------------------------------------------
def get_graph(link):
  ret = {}
  for item in link:
    if item["type"] != "Bound":
      ret[item["to"]] = item["from"]
  return ret

# --------------------------------------------------------------------------
##
# @brief Get type of all links
#
# @param link  link in regulation network
#
# @returns   type of all links in regulation network
#
# --------------------------------------------------------------------------
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

    if item["inducer"] == "Positive":
      inducer_type[item["to"]] = "Inducer"
    elif item["inducer"] == "Negative":
      inducer_type[item["to"]] = "Corepressor"
    else:
      inducer_type[item["to"]] = "None"
  return link_type, inducer_type

# --------------------------------------------------------------------------
##
# @brief Get gene circuit with regulation network
#
# @param network   regulation network
# @param database  database instance
#
# @returns   gene circuit
#
# --------------------------------------------------------------------------
def dump_group(network, database):
  graph = get_graph(network["link"])
  link_type, inducer_type = get_graph_type(network["link"])
  data, b_list, pro_pos = work(network, database)
  groups = {}
  proteins = {}
  plasmid = []

  # get group info
  for i in data:
    grp = []
    # get name and type of group member
    for elem in data[i]:
      xml_file = find_file(elem + ".xml", ".")
      grp.append({"name": elem, "type": component_union.get_part_type(xml_file)})
    for idx in range(1, len(grp) - 1, 2):
      grp[idx]["type"] = "RBS"
    grp[0]["type"] = "Promoter"
    grp[-1]["type"] = "Terminator"

    # get link type and inducer type
    prev = -1
    l_type = "Constitutive"
    i_type = "None"
    for j in b_list:
      if b_list[j] == i and j in graph:
        prev = graph[j]
        l_type = link_type[j]
        i_type = inducer_type[j]
        break
    groups[i] = {"sbol":grp, "state": "cis", "type": l_type,\
        "corep_ind_type": i_type, "from": prev, "to": []}
    plasmid.append(i)

  # get next nodes of a group
  for i in graph:
    groups[b_list[graph[i]]]["to"].append(i)
  for i in b_list:
    cur_group = groups[b_list[i]]
    # add id of proteins in a group
    groups[b_list[i]]["sbol"][pro_pos[i]]["id"] = i

    # get protein info
    ## get coresponding repressor
    prev_node = cur_group["from"]
    if prev_node != -1:
      prev_grp = groups[b_list[prev_node]]
      regulator = prev_grp["sbol"][pro_pos[prev_node]]["name"]
    else:
      regulator = None
    ## get inducer of a link
    corep_ind_type = cur_group["corep_ind_type"]
    if corep_ind_type != "None" and cur_group["type"] == "Positive":
      inducer = database.find_inducer_with_activator(regulator, corep_ind_type)
      groups[b_list[i]]["corep_ind"] = inducer["Number"]
    if corep_ind_type != "None" and cur_group["type"] == "Negative":
      inducer = database.find_inducer_with_activator(regulator, corep_ind_type)
      groups[b_list[i]]["corep_ind"] = inducer["Number"]
    ## get protein info
    proteins[i] = get_pro_info(database, pro_pos[i], groups, b_list[i],\
        regulator)

  # do not display regulation protein
  for part in network["part"]:
    pro_id = part["id"]
    grp_id = proteins[pro_id]["grp_id"]
    pos = proteins[pro_id]["pos"]
    proteins[pro_id]["display"] = part["type"] == "Protein"
    groups[grp_id]["sbol"][pos]["type"] = part["type"]


  # update_proteins_repress(database, proteins, groups)
  gene_circuit = {"groups": groups, "proteins": proteins, "plasmids": [plasmid]}
  update_proteins_repress(database, gene_circuit)
  return gene_circuit

# --------------------------------------------------------------------------
##
# @brief  get promoter parameter type
#
# @param p_type link type
#
# @returns   promoter paramter type
#
# --------------------------------------------------------------------------
def get_type_of_promoter(p_type):
  if p_type == "Constitutive":
    return "PoPS"
  elif p_type == "Negative":
    return "MPPromoter"
  elif p_type == "Positive":
    return "LeakageRate"

# --------------------------------------------------------------------------
##
# @brief Format data from javascript to use in python
#
# @param gene_circuit  gene circuit
#
# @returns   formatted data
#
# --------------------------------------------------------------------------
def js_formatter(gene_circuit):
  return gene_circuit
  new_proteins = {}
  for i in gene_circuit["proteins"]:
    new_proteins[int(i)] = gene_circuit["proteins"][i]
  gene_circuit["proteins"] = new_proteins

  new_groups = {}
  for i in gene_circuit["groups"]:
    new_groups[int(i)] = gene_circuit["groups"][i]
  gene_circuit["groups"] = new_groups
  return gene_circuit

# --------------------------------------------------------------------------
##
# @brief update gene circuit
#
# @param db           database instance
# @param update_info  update detail and gene circuit
#
# @returns   updated gene circuit
#
# --------------------------------------------------------------------------
def update_controller(db, update_info):
  gene_circuit = js_formatter(update_info["gene_circuit"])
  # regulator_list = [name for name in gene_circuit["proteins"]]
  regulator_list = [i["name"] for i in gene_circuit["proteins"].values() if
      not i["display"]]
  detail = update_info["detail"]
  pro_id = detail["pro_id"]
  protein = gene_circuit["proteins"][pro_id]
  pro_name = protein["name"]
  pro_idx = protein["pos"]
  grp_id = protein["grp_id"]
  group = gene_circuit["groups"][grp_id]
  if detail["type"] == "RiPS":
    rbs_value = float(detail["new_value"])
    # idx = get_index_in_group(pro_name, group["sbol"])
    bestRBS = db.getRBSNearValue(rbs_value)
    gene_circuit["groups"][grp_id]["sbol"][pro_idx - 1]["name"] = bestRBS["Number"]
    gene_circuit["proteins"][pro_id]["RiPS"] = bestRBS["MPRBS"]

  elif detail["type"] == "copy":
    for plasmid in gene_circuit["plasmids"]:
      for item in plasmid:
        if item == grp_id:
          updated_plasmid = plasmid
          break
    ideal_value = detail["new_value"]
    best_value = db.getPlasmidBackboneNearValue(ideal_value)["CopyNumber"]
    for i in gene_circuit["proteins"]:
      if gene_circuit["proteins"][i]["grp_id"] in updated_plasmid:
        gene_circuit["proteins"][i]["copy"] = best_value

  elif detail["type"] == "PoPS" or detail["type"] == "K1":
    link_type = group["type"]
    p_type = get_type_of_promoter(link_type)
    # pre_work, find best_promoter and best_repressor
    if detail["type"] == "PoPS":
      promoter_value = float(detail["new_value"])
      #select best promoter according to link type
      if link_type == "Positive":
        best_promoter = db.getActivatedPromoterNearValue(promoter_value,\
            regulator_list, link_type, p_type)
        best_regulator = db.find_activator_with_promoter(best_promoter["Number"])
        regulator_value = log10(best_regulator["K1"])
      elif link_type == "Negative":
        best_promoter = db.getRepressedPromoterNearValue(promoter_value,\
            regulator_list, link_type, p_type)
        best_regulator = db.find_repressor_with_promoter(best_promoter["Number"])
        regulator_value = log10(best_regulator["K1"])
      else:
        best_promoter = db.getRepressedPromoterNearValue(promoter_value,\
            [], link_type, p_type)
    else:
      regulator_value = pow(10, float(detail["new_value"]))
      if link_type == "Positive":
        best_regulator = db.getActivatorNearValue(regulator_value, regulator_list)
        best_promoter = find_promoter(db, activator=best_regulator["Number"])
        promoter_value = best_promoter[p_type]
      else:
        best_regulator = db.getRepressorNearValue(regulator_value, regulator_list)
        best_promoter = find_promoter(db, repressor=best_regulator["Number"])
        promoter_value = best_promoter[p_type]

    # update corresponding repressor
    prev_node = group["from"]
    regulator = None
    # update related promoters
    if detail["type"] == "PoPS":
      gene_circuit["groups"][grp_id]["sbol"][0]["name"] = best_promoter["Number"]
      for j in range(2, len(group["sbol"]), 2):
        pro2_id = gene_circuit["groups"][grp_id]["sbol"][j]["id"]
        gene_circuit["proteins"][pro2_id]["PoPS"] = best_promoter[p_type]

    if prev_node != -1:
      prev_grp = gene_circuit["proteins"][prev_node]["grp_id"]
      prev_pos = gene_circuit["proteins"][prev_node]["pos"]
      gene_circuit["proteins"][prev_node]["K1"] = regulator_value
      gene_circuit["proteins"][prev_node]["name"] = best_regulator["Number"]
      gene_circuit["groups"][prev_grp]["sbol"][prev_pos]["name"] = best_regulator["Number"]

      # update related promoters
      for i in gene_circuit["groups"]:
        if gene_circuit["groups"][i]["from"] == prev_node:
          gene_circuit["groups"][i]["sbol"][0]["name"] = best_promoter["Number"]
          for j in range(2, len(gene_circuit["groups"][i]["sbol"]), 2):
            pro2_id = gene_circuit["groups"][i]["sbol"][j]["id"]
            gene_circuit["proteins"][pro2_id]["PoPS"] = best_promoter[p_type]

  update_proteins_repress(db, gene_circuit)
  return gene_circuit

if __name__ == "__main__":
  db = database.SqliteDatabase()
  print dump_group(data, db)
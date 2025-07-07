import json
import time
import logging


class StatisticsHelper:
    def __init__(self):
        self.statistics = {"NP": {"identified": {},
                                  "missed_declined_annotations": []}, "cache": {"hit": {}, "miss": {}}, "gpt": {"error": []},
                           "validation": {}}

    def __check_create_in_dict(self, obj, name) -> None:
        if name not in obj.keys():
            obj[name] = {}

    # Cache
    def sh_set_cache_hit(self, item):
        self.__check_create_in_dict(self.statistics["cache"]["hit"], item)
        self.statistics["cache"]["hit"][item]["last_hit"] = time.time()

    def sh_set_cache_miss(self, item):
        self.__check_create_in_dict(self.statistics["cache"]["miss"], item)
        self.statistics["cache"]["miss"][item]["last_miss"] = time.time()

    # NP
    def sh_set_np(self, np, np_normalized):
        self.__check_create_in_dict(self.statistics["NP"]["identified"], np)
        self.statistics["NP"]["identified"][np] = {
            "normalized": np_normalized, "annotation": ""}

    def sh_set_np_missing_annotation(self, np):
        self.statistics["NP"]["missed_declined_annotations"].append(np)

    def sh_set_np_annotation(self, np, annotation):
        """
        You need to perform set_np before you set annotation status here
        """
        self.statistics["NP"]["identified"][np]["annotation"] = annotation

    # Validator
    def sh_set_validation_error(self, item, message):
        self.statistics["validation"][item] = message

    # AI Services Errors
    def sh_set_ai_error(self, cell, np_detection):
        self.statistics["ai"]["error"].append({cell: np_detection})

    # Others
    def sh_persist_data(self):
        with open("./statistics.json", "w") as statistics_file:
            json.dump(self.statistics, statistics_file, indent=4)

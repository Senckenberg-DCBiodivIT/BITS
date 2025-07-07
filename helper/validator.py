import logging
import copy


class Validator():

    def vh_bijective_validation(self) -> None:
        logging.debug(f"vh_bijective_validation")
        error_flag = False

        if len(self.original_json_loads) != len(self.load_json_loads):
            self.sH_set_validation_error("different_length", True)

        for item_index in range(len(self.load_json_loads)):  # Rows
            for language in self.relevant_fields.keys():
                for field in self.relevant_fields[language]:
                    if field in self.load_json_loads[item_index].keys():
                        original_field = self.original_json_loads[item_index][field]
                        annotated_field = self.load_json_loads[item_index][field]

                        comparison = self.__compare_cells(
                            original_field, annotated_field)

                        if comparison == False:
                            error_flag = True
                            self.sh_set_validation_error(
                                f"{original_field}", f"{annotated_field}")

                        if error_flag != True:
                            self.sh_set_validation_error(
                                f"Error detected", f"False")

    def __compare_cells(self, original, annotated):
        copy_annotated = copy.deepcopy(annotated)

        for key, value in self.bh_request_results.items():
            if value != {}:
                value_replace = f"{{'{key}': {value}}}"
                copy_annotated = copy_annotated.replace(value_replace, key)

        return True if copy_annotated == original else False

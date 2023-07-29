import yaml
import glob
from database import ItemRequireComputeSpec, ItemRequire, Database


def execute_request_from_file(instance: Database, name: str):
    file_name = f"test/{name}"
    with open(file_name,encoding="utf8") as fp:
        node = yaml.safe_load(fp)
    spec = ItemRequireComputeSpec()
    spec.factories = node["factories"]
    spec.item_output_minute = ItemRequire()
    spec.item_output_minute.name = node["item_output_minute"]["name"]
    spec.item_output_minute.amount = node["item_output_minute"]["amount"]
    result = instance.compute_item_factories(spec)
    print(f"factories count for producing item:{spec.item_output_minute.name} "
          f"{spec.item_output_minute.amount} per minute\n{result}")


if __name__ == '__main__':
    db_name = "databases/factorio.yaml"
    db = Database.create_from_file(db_name)
    spec_files= glob.glob1("test","*.yaml")
    for spec_file in spec_files:
        print(f"computing spec:{spec_file}")
        execute_request_from_file(db, spec_file)

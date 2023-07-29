from __future__ import annotations

import math

import yaml


class ItemRequire:
    name: str
    amount: int


class Item:
    name: str
    supported_factories: [str]


class FactoryItem(Item):
    amount: int
    speed_seconds: float
    requires: list[ItemRequire]

    def unity_speed(self) -> float:
        return self.amount / self.speed_seconds

    def require_unity_speed(self) -> dict[str, float]:
        result: dict[str, float] = {}
        for require in self.requires:
            result[require.name] = require.amount/self.speed_seconds
        return result


class TransportBelt(FactoryItem):
    throughput: int
    density: int
    pass


class ItemFactory:
    name: str
    speed_magnification: float


class ItemRequireComputeSpec:
    item_output_minute: ItemRequire
    items_bus: list[str]
    transport_belt: str
    factories: list[str]
    pass


class ItemFactoryAssign:
    item: FactoryItem
    factory: ItemFactory

    def unity_speed(self) -> float:
        return self.item.unity_speed() * self.factory.speed_magnification

    def require_unity_speed(self) -> dict[str, float]:
        base_speeds = self.item.require_unity_speed()
        result_speeds = dict(base_speeds)
        for name in result_speeds:
            result_speeds[name] = base_speeds[name] * self.factory.speed_magnification
        return result_speeds


class Database:
    _items: dict[str, FactoryItem]
    _factories: dict[str, ItemFactory]

    @classmethod
    def create_from_file(cls, file_name: str) -> Database:
        with open(file_name,encoding="utf8") as fp:
            node = yaml.safe_load(fp)

        raw_items = node["items"]
        items: dict[str, FactoryItem] = {}
        for raw_item in raw_items:  # type:dict
            item: FactoryItem
            if "throughput" in raw_item:
                typed_item = TransportBelt()
                cls.apply_transport_belt(typed_item, raw_item)
                cls.apply_factory_item(typed_item, raw_item)
                cls.apply_item(typed_item, raw_item)
                item = typed_item
            elif "amount" in raw_item:
                typed_item = FactoryItem()
                cls.apply_factory_item(typed_item, raw_item)
                cls.apply_item(typed_item, raw_item)
                item = typed_item
            else:
                raise f"not supported item:{raw_item}"
            items[item.name] = item
        raw_factories = node["factories"]
        factories: dict[str, ItemFactory] = {}
        for raw_factory in raw_factories:
            factory = ItemFactory()
            factory.name = raw_factory["name"]
            factory.speed_magnification = raw_factory["speed_magnification"]
            factories[factory.name] = factory
        db = Database()
        db._items = items
        db._factories = factories
        return db

    @classmethod
    def apply_item(cls, item: Item, raw_item: dict):
        item.name = raw_item["name"]
        item.supported_factories = raw_item["supported_factories"]

    @classmethod
    def apply_factory_item(cls, item: FactoryItem, raw_item: dict):
        item.amount = raw_item["amount"]
        item.speed_seconds = raw_item["speed_seconds"]
        raw_requires = raw_item.get("requires")
        requires: list[ItemRequire] = []
        if raw_requires is not None:
            for raw_require in raw_requires:
                require: ItemRequire = ItemRequire()
                require.amount = raw_require["amount"]
                require.name = raw_require["name"]
                requires.append(require)
        item.requires = requires

    @classmethod
    def apply_transport_belt(cls, item: TransportBelt, raw_item: dict):
        item.throughput = raw_item["throughput"]
        item.density = raw_item["density"]

    def compute_item_factories(self, spec: ItemRequireComputeSpec) -> dict[str, int]:
        item = self._items[spec.item_output_minute.name]
        unity_item_factories: dict[str, float] = {}
        factory_factor = spec.item_output_minute.amount * 1.0 / 60
        self._compute_unity_item_factories(item, factory_factor, spec.factories, unity_item_factories)
        item_factory_amounts: dict[str, int] = {}
        for item_name in unity_item_factories:
            item_factory_amounts[item_name] = math.ceil(unity_item_factories[item_name])
        return item_factory_amounts

    def _compute_unity_item_factories(self, item: FactoryItem,
                                      factory_factor: float,
                                      pinned_factories: list[str],
                                      item_factories: dict[str, float]):
        item_factory = self._item_factory(item, pinned_factories)
        assign = ItemFactoryAssign()
        assign.item = item
        assign.factory = item_factory
        unity_factory_amount = factory_factor * (1 / assign.unity_speed())
        last_item_factory_amount = item_factories.get(item.name)
        if last_item_factory_amount is None:
            item_factories[item.name] = unity_factory_amount
        else:
            item_factories[item.name] = last_item_factory_amount + unity_factory_amount
        require_unity_speeds = assign.require_unity_speed()
        for require_item_name in require_unity_speeds:
            require_item_speed = require_unity_speeds[require_item_name]
            require_item = self._items.get(require_item_name)
            if require_item is None:
                raise Exception(f"require item:{require_item_name} not found")
            self._compute_unity_item_factories(require_item, require_item_speed*unity_factory_amount,
                                               pinned_factories, item_factories)
        pass

    def _item_factory(self, item: Item, factories: list[str]) -> ItemFactory:
        max_factory_magnification: float = 0
        max_factory: ItemFactory | None = None
        for supported_factory in item.supported_factories:
            if supported_factory in factories:
                return self._factories[supported_factory]
            factory = self._factories[supported_factory]
            if factory.speed_magnification > max_factory_magnification:
                max_factory_magnification = factory.speed_magnification
                max_factory = factory
        if max_factory is None:
            raise "no factory"
        return max_factory

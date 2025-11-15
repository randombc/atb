from core.navigation import NavigationNode
from scripts import get_product_keys


class Licenses(NavigationNode):
    def get_name(self) -> str:
        return "Licenses"

    def process(self):
        get_product_keys.main()

        self.wait_back()
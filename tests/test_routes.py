######################################################################
# Copyright 2016, 2024 John J. Rofrano. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
######################################################################

"""
TestYourResourceModel API Service Test Suite
"""

# pylint: disable=duplicate-code
import os
import logging
from unittest import TestCase
from wsgi import app
from service.common import status
from service.models import db, Shopcart
from tests.factories import ShopcartFactory, ItemFactory

DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql+psycopg://postgres:postgres@localhost:5432/testdb"
)

BASE_URL = "/api/shopcarts"


######################################################################
#  T E S T   C A S E S
######################################################################
# pylint: disable=too-many-public-methods
class TestShopcartService(TestCase):
    """REST API Server Tests"""

    @classmethod
    def setUpClass(cls):
        """Run once before all tests"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        # Set up the test database
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        app.app_context().push()

    @classmethod
    def tearDownClass(cls):
        """Run once after all tests"""
        db.session.close()

    def setUp(self):
        """Runs before each test"""
        self.client = app.test_client()
        db.session.query(Shopcart).delete()  # clean up the last tests
        db.session.commit()

    def tearDown(self):
        """This runs after each test"""
        db.session.remove()

    ######################################################################
    #  H E L P E R   M E T H O D S
    ######################################################################

    def _create_shopcarts(self, count, name=None) -> list:
        """Factory method to create shopcarts in bulk"""
        shopcarts = []

        for i in range(count):
            shopcart = ShopcartFactory(name=name if name else f"shopcart{i}")
            resp = self.client.post(BASE_URL, json=shopcart.serialize())
            self.assertEqual(
                resp.status_code,
                status.HTTP_201_CREATED,
                "Could not create test Shopcart",
            )
            new_shopcart = resp.get_json()
            shopcart.id = new_shopcart["id"]
            shopcarts.append(shopcart)

        return shopcarts

    ######################################################################
    #  T E S T   C A S E S
    ######################################################################

    def test_health(self):
        """It should be healthy"""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(data["status"], 200)
        self.assertEqual(data["message"], "Healthy")

    ######################################################################
    #  S H O P C A R T   T E S T   C A S E S
    ######################################################################

    # ----------------------------------------------------------
    # TEST CREATE
    # ----------------------------------------------------------
    def test_create_shopcart(self):
        """It should Create a new Shopcart"""
        shopcart = ShopcartFactory()
        resp = self.client.post(
            BASE_URL, json=shopcart.serialize(), content_type="application/json"
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

        # Make sure location header is set
        location = resp.headers.get("Location", None)
        self.assertIsNotNone(location)

        # Check the data is correct
        new_shopcart = resp.get_json()
        self.assertEqual(new_shopcart["name"], shopcart.name, "Names does not match")

        # Check that the location header was correct by getting it
        resp = self.client.get(location, content_type="application/json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        new_shopcart = resp.get_json()
        self.assertEqual(new_shopcart["name"], shopcart.name, "Names does not match")

    # ----------------------------------------------------------
    # TEST READ
    # ----------------------------------------------------------
    def test_get_shopcart(self):
        """It should Get a single Shopcart"""
        test_shopcart = self._create_shopcarts(1)[0]
        resp = self.client.get(f"/api/shopcarts/{test_shopcart.id}")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertEqual(data["name"], test_shopcart.name)

    # ----------------------------------------------------------
    # TEST UPDATE
    # ----------------------------------------------------------
    def test_update_shopcart(self):
        """It should Update an existing shopcarts"""
        # create a shopcart to update
        test_shopcart = ShopcartFactory()
        resp = self.client.post(BASE_URL, json=test_shopcart.serialize())
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

        # update the shopcart
        new_shopcart = resp.get_json()
        new_shopcart["name"] = "special_shopcart"
        new_shopcart_id = new_shopcart["id"]
        resp = self.client.put(f"{BASE_URL}/{new_shopcart_id}", json=new_shopcart)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        updated_shopcart = resp.get_json()
        self.assertEqual(updated_shopcart["name"], "special_shopcart")

    def test_update_nonexistent_shopcart(self):
        """It should return 404 when updating a shopcart that does not exist"""
        update_data = {"name": "some_name"}
        resp = self.client.put(f"{BASE_URL}/0", json=update_data)
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    # ----------------------------------------------------------
    # TEST DELETE
    # ----------------------------------------------------------
    def test_delete_shopcart(self):
        """It should delete a Shopcart"""
        test_shopcart = self._create_shopcarts(1)[0]
        resp = self.client.delete(f"{BASE_URL}/{test_shopcart.id}")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(len(resp.data), 0)
        # make sure they are deleted
        resp = self.client.get(f"{BASE_URL}/{test_shopcart.id}")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_non_exist_shopcart(self):
        """It should Delete a Shopcart even if it does not exist"""
        resp = self.client.delete(f"{BASE_URL}/0")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(len(resp.data), 0)

    # ----------------------------------------------------------
    # TEST LIST
    # ----------------------------------------------------------
    def test_list_shopcarts(self):
        """It should Get a list of Shopcarts and filter by name"""
        # Create 5 shopcarts with default names
        self._create_shopcarts(5)

        self._create_shopcarts(1, name="special_shopcart")

        # Test getting all shopcarts
        resp = self.client.get(BASE_URL)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertEqual(len(data), 6)

        # Test getting shopcarts by name
        resp = self.client.get(BASE_URL + "?name=special_shopcart")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "special_shopcart")

    # ----------------------------------------------------------
    # TEST BAD ROUTES
    # ----------------------------------------------------------

    def test_bad_request(self):
        """It should not Create when sending the wrong data"""
        resp = self.client.post(BASE_URL, json={"name": "not enough data"})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unsupported_media_type(self):
        """It should not Create when sending wrong media type"""
        shopcart = ShopcartFactory()
        resp = self.client.post(
            BASE_URL, json=shopcart.serialize(), content_type="test/html"
        )
        self.assertEqual(resp.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    def test_method_not_allowed(self):
        """It should not allow an illegal method call"""
        resp = self.client.put(BASE_URL, json={"not": "today"})
        self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    ######################################################################
    #  I T E M   T E S T   C A S E S
    ######################################################################

    # ----------------------------------------------------------
    # TEST CREATE
    # ----------------------------------------------------------

    def test_add_item(self):
        """It should create a new item and add to a shopcart"""
        shopcart = self._create_shopcarts(1)[0]
        item = ItemFactory()
        resp = self.client.post(
            f"{BASE_URL}/{shopcart.id}/items",
            json=item.serialize(),
            content_type="application/json",
        )

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

        # Make sure location header is set
        location = resp.headers.get("Location", None)
        self.assertIsNotNone(location)

        data = resp.get_json()
        logging.debug(data)
        self.assertEqual(str(data["shopcart_id"]), str(shopcart.id))
        self.assertEqual(str(data["item_id"]), str(item.item_id))
        self.assertEqual(data["description"], item.description)
        self.assertEqual(str(data["quantity"]), str(item.quantity))
        self.assertEqual(str(data["price"]), str(item.price))

        # Check that the location header was correct by getting it
        resp = self.client.get(location, content_type="application/json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        new_item = resp.get_json()
        # Converting both to string for comparison
        self.assertEqual(
            str(new_item["item_id"]), str(item.item_id), "item name does not match"
        )

    def test_add_item_not_found(self):
        """It should return 404 when trying to add to a shopcart does not exist"""
        # Create a shopcart and delete it instantly
        shopcart = self._create_shopcarts(1)[0]

        resp = self.client.delete(f"{BASE_URL}/{shopcart.id}")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(len(resp.data), 0)

        # Add an item to the shopcart should fail
        item = ItemFactory()
        resp = self.client.post(
            f"{BASE_URL}/{shopcart.id}/items",
            json=item.serialize(),
            content_type="application/json",
        )

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    # ----------------------------------------------------------
    # TEST READ
    # ----------------------------------------------------------
    def test_read_an_item(self):
        """It should Read an item from an shopcart"""
        # create a known item
        shopcart = self._create_shopcarts(1)[0]
        item = ItemFactory()
        resp = self.client.post(
            f"{BASE_URL}/{shopcart.id}/items",
            json=item.serialize(),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

        data = resp.get_json()
        logging.debug(data)
        item_id = data["id"]

        # retrieve it back
        resp = self.client.get(
            f"{BASE_URL}/{shopcart.id}/items/{item_id}",
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        data = resp.get_json()
        logging.debug(data)
        self.assertEqual(str(data["shopcart_id"]), str(shopcart.id))
        self.assertEqual(str(data["item_id"]), str(item.item_id))
        self.assertEqual(data["description"], item.description)
        self.assertEqual(str(data["quantity"]), str(item.quantity))
        self.assertEqual(str(data["price"]), str(item.price))

    # ----------------------------------------------------------
    # TEST UPDATE
    # ----------------------------------------------------------

    def test_update_item(self):
        """It should Update an Item in a shopcart"""
        # create a item
        shopcart = self._create_shopcarts(1)[0]
        item = ItemFactory()
        resp = self.client.post(
            f"{BASE_URL}/{shopcart.id}/items",
            json=item.serialize(),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

        data = resp.get_json()
        logging.debug(data)
        item_id = data["id"]
        item_desc = data["description"]
        item_price = data["price"]
        data["item_id"] = "ABC1234"
        data["quantity"] = 56789

        # send the update back
        resp = self.client.put(
            f"{BASE_URL}/{shopcart.id}/items/{item_id}",
            json=data,
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        # retrieve it back
        resp = self.client.get(
            f"{BASE_URL}/{shopcart.id}/items/{item_id}",
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        data = resp.get_json()
        logging.debug(data)
        self.assertEqual(data["id"], item_id)
        self.assertEqual(data["item_id"], "ABC1234")
        self.assertEqual(data["description"], item_desc)
        self.assertEqual(data["quantity"], 56789)
        self.assertEqual(data["price"], item_price)

    # ----------------------------------------------------------
    # TEST DELETE
    # ----------------------------------------------------------
    def test_delete_item_from_shopcart(self):
        """It should delete an Item from a Shopcart"""
        # Create a shopcart
        shopcart = ShopcartFactory()
        resp = self.client.post(BASE_URL, json=shopcart.serialize())
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        new_shopcart = resp.get_json()

        # Add an item to the shopcart and explicitly pass shopcart_id
        item = ItemFactory(shopcart_id=new_shopcart["id"])
        resp = self.client.post(
            f"{BASE_URL}/{new_shopcart['id']}/items", json=item.serialize()
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        new_item = resp.get_json()

        # Delete the item from the shopcart
        resp = self.client.delete(
            f"{BASE_URL}/{new_shopcart['id']}/items/{new_item['id']}"
        )
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

        # Verify the item is no longer in the shopcart
        resp = self.client.get(
            f"{BASE_URL}/{new_shopcart['id']}/items/{new_item['id']}"
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_item_not_found(self):
        """It should return 204 when trying to delete an item that does not exist"""
        # Create a shopcart
        shopcart = ShopcartFactory()
        resp = self.client.post(BASE_URL, json=shopcart.serialize())
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        new_shopcart = resp.get_json()

        # Try deleting a non-existing item
        resp = self.client.delete(
            f"{BASE_URL}/{new_shopcart['id']}/items/0"
        )  # ID 0 doesn't exist
        self.assertEqual(
            resp.status_code, status.HTTP_204_NO_CONTENT
        )  # Expect 204 for non-existent item

    # ----------------------------------------------------------
    # TEST LIST
    # ----------------------------------------------------------
    def test_list_items_in_shopcart(self):
        """It should List all items in a particular Shopcart"""
        # Create a shopcart
        shopcart = ShopcartFactory()
        resp = self.client.post(BASE_URL, json=shopcart.serialize())
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        new_shopcart = resp.get_json()

        # Add multiple items to the shopcart
        item1 = ItemFactory(shopcart_id=new_shopcart["id"], quantity=2, price=10)
        item2 = ItemFactory(shopcart_id=new_shopcart["id"], quantity=5, price=20.0)

        # Add item1
        resp = self.client.post(
            f"{BASE_URL}/{new_shopcart['id']}/items", json=item1.serialize()
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

        # Add item2
        resp = self.client.post(
            f"{BASE_URL}/{new_shopcart['id']}/items", json=item2.serialize()
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

        # Retrieve all items in the shopcart
        resp = self.client.get(f"{BASE_URL}/{new_shopcart['id']}/items")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # Verify the response contains both items
        data = resp.get_json()
        self.assertEqual(len(data), 2)

        # Convert item_id from response to int and ensure the items returned are the ones we added
        self.assertEqual(int(data[0]["item_id"]), item1.item_id)
        self.assertEqual(int(data[1]["item_id"]), item2.item_id)

        rep = False

        if int(data[0]["item_id"]) == int(data[1]["item_id"]):
            rep = True

        # Test query by `price`
        resp = self.client.get(f"{BASE_URL}/{new_shopcart['id']}/items?price=10")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()

        self.assertEqual(len(data), 1)
        self.assertEqual(float(data[0]["price"]), 10.0)

        # Test query by `quantity`
        resp = self.client.get(f"{BASE_URL}/{new_shopcart['id']}/items?quantity=5")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertEqual(len(data), 1)
        self.assertEqual(int(data[0]["quantity"]), 5)

        # Test query by `item_id`
        resp = self.client.get(
            f"{BASE_URL}/{new_shopcart['id']}/items?item_id={item1.item_id}"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        if rep:
            self.assertEqual(len(data), 2)
        else:
            self.assertEqual(len(data), 1)
        self.assertEqual(int(data[0]["item_id"]), item1.item_id)

    ######################################################################
    #  A C T I O N S   T E S T   C A S E S
    ######################################################################

    def test_clear_shopcart(self):
        """After a clear action is requested, no item should be in the shopcart"""

        # Create a shopcart
        shopcart = ShopcartFactory()
        resp = self.client.post(BASE_URL, json=shopcart.serialize())
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        new_shopcart = resp.get_json()

        # Add multiple items to the shopcart
        item1 = ItemFactory(shopcart_id=new_shopcart["id"])
        item2 = ItemFactory(shopcart_id=new_shopcart["id"])

        # Add item1
        resp = self.client.post(
            f"{BASE_URL}/{new_shopcart['id']}/items", json=item1.serialize()
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

        # Add item2
        resp = self.client.post(
            f"{BASE_URL}/{new_shopcart['id']}/items", json=item2.serialize()
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

        # Ensure now the shopcart has 2 items
        resp = self.client.get(f"{BASE_URL}/{new_shopcart['id']}/items")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertEqual(len(data), 2)

        # Make a clear request
        resp = self.client.put(f"{BASE_URL}/{new_shopcart['id']}/clear")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        # Ensure now the shopcart has no item
        resp = self.client.get(f"{BASE_URL}/{new_shopcart['id']}/items")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertEqual(len(data), 0)

    def test_clear_nonexistent_shopcart(self):
        """Request clear for a nonexistent shopcart will get error 404"""

        # Create a shopcart
        shopcart = ShopcartFactory()
        resp = self.client.post(BASE_URL, json=shopcart.serialize())
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

        # Delete the shopcart
        resp = self.client.delete(f"{BASE_URL}/{shopcart.id}")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(len(resp.data), 0)

        resp = self.client.put(f"{BASE_URL}/{shopcart.id}/clear")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    # ----------------------------------------------------------
    #  Calculate Price
    # ----------------------------------------------------------

    # def test_calculate_selected_price(self):
    #     """It should calculate the total price of selected items in a shopcart"""

    #     # Create a shopcart
    #     shopcart = self._create_shopcarts(1)[0]

    #     item1 = ItemFactory(shopcart_id=shopcart.id, price=10, quantity=1)
    #     item2 = ItemFactory(shopcart_id=shopcart.id, price=20, quantity=1)
    #     item3 = ItemFactory(shopcart_id=shopcart.id, price=30, quantity=1)

    #     # Add item 1
    #     resp = self.client.post(
    #         f"{BASE_URL}/{shopcart.id}/items",
    #         json=item1.serialize(),
    #         content_type="application/json",
    #     )
    #     self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    #     # Add item 2
    #     resp = self.client.post(
    #         f"{BASE_URL}/{shopcart.id}/items",
    #         json=item2.serialize(),
    #         content_type="application/json",
    #     )
    #     self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    #     # Add item 3
    #     resp = self.client.post(
    #         f"{BASE_URL}/{shopcart.id}/items",
    #         json=item3.serialize(),
    #         content_type="application/json",
    #     )
    #     self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    #     selected_items = [int(item1.item_id), int(item3.item_id)]
    #     resp = self.client.post(
    #         f"{BASE_URL}/{shopcart.id}/calculate_total_price",
    #         json={"selected_items": selected_items},
    #         content_type="application/json",
    #     )
    #     self.assertEqual(resp.status_code, status.HTTP_200_OK)
    #     data = resp.get_json()

    #     expected_total_price = 10 + 30
    #     self.assertEqual(data["total_price"], expected_total_price)

    def test_calculate_total_price(self):
        """It should calculate the total price of items in a shopcart"""

        # Create a shopcart
        shopcart = self._create_shopcarts(1)[0]

        item1 = ItemFactory(shopcart_id=shopcart.id, price=10, quantity=1)
        item2 = ItemFactory(shopcart_id=shopcart.id, price=20, quantity=1)
        item3 = ItemFactory(shopcart_id=shopcart.id, price=30, quantity=1)

        # Add item 1
        resp = self.client.post(
            f"{BASE_URL}/{shopcart.id}/items",
            json=item1.serialize(),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

        # Add item 2
        resp = self.client.post(
            f"{BASE_URL}/{shopcart.id}/items",
            json=item2.serialize(),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

        # Add item 3
        resp = self.client.post(
            f"{BASE_URL}/{shopcart.id}/items",
            json=item3.serialize(),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

        resp = self.client.get(
            f"{BASE_URL}/{shopcart.id}/calculate_total_price",
            content_type="application/json",
        )

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()

        expected_total_price = 10 + 20 + 30
        self.assertEqual(data["total_price"], expected_total_price)

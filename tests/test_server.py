# Test cases can be run with:
# nosetests
# coverage report -m

""" Test cases for the Recommendation Service """
import os
import logging
import unittest
import json
from mock import MagicMock, patch
from flask_api import status    # HTTP Status Codes
import server
import mock
from models import db, init_db
from models import Recommendation, RecommendationType
from connection import get_database_uri

os.environ['TEST'] = 'True'

######################################################################
#  T E S T   C A S E S
######################################################################
class TestRecommendationServer(unittest.TestCase):
    """ Recommendation Server Tests """

    @classmethod
    def setUpClass(cls):
        """ Run once before all tests """
        server.app.debug = False
        server.initialize_logging(logging.INFO)

    def setUp(self):
        """ Runs before each test """
        server.initialize_db()

        rec_type = RecommendationType.find_by_id(1)
        rec = Recommendation(10, rec_type)
        rec.dislike_count = 1
        rec_detail1 = RecommendationDetail(55, .9)
        rec.recommendations.append(rec_detail1)
        rec.save()

        rec_type = RecommendationType.find_by_id(2)
        rec = Recommendation(20, rec_type)
        rec.dislike_count = 2
        rec_detail1 = RecommendationDetail(66, .8)
        rec.recommendations.append(rec_detail1)
        rec.save()

        rec_type = RecommendationType.find_by_id(3)
        rec = Recommendation(30, rec_type)
        rec_detail1 = RecommendationDetail(77, .7)
        rec.dislike_count = 3
        rec.recommendations.append(rec_detail1)
        rec.save()

        rec_type = RecommendationType.find_by_id(1)
        rec = Recommendation(40, rec_type)
        rec.dislike_count = 4
        rec_detail1 = RecommendationDetail(88, .6)
        rec.recommendations.append(rec_detail1)
        rec.save()

        self.app = server.app.test_client()

    def tearDown(self):
        """ Runs after each test """
        db.session.remove()
        db.drop_all()

    def test_index_view(self):
        """ Test the Home Page """
        resp = self.app.get('/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue('Recommendation Demo REST API Service' in resp.data)

    def test_metadata_view(self):
        """ Test the Metadata Page """
        resp = self.app.get('/recommendations/metadata')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue('Manage Product Category Metadata' in resp.data)

    def test_docs_view(self):
        """ Test the Documentations Page """
        resp = self.app.get('/recommendations/docs')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue('Documentation' in resp.data)

    def test_manage_view(self):
        """ Test the Manage Recommendations Page """
        resp = self.app.get('/recommendations/manage')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue('Manage Recommendations' in resp.data)

    def test_get_recommendation_list(self):
        """ Get a list of Recommendation """
        resp = self.app.get('/recommendations')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(json.loads(resp.data)), 4)

    def test_query_recommendation_list_by_type(self):
        """ Query Recommendation By Type """
        resp = self.app.get('/recommendations?type=up-sell')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(json.loads(resp.data)), 2)

    def test_query_recommendation_list_by_product(self):
        """ Query Recommendation By Product Id """
        resp = self.app.get('/recommendations?product_id=10')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(json.loads(resp.data)), 1)

    def test_query_recommendation_list_by_product_id_and_type_id(self):
        """ Query Recommendation By Product Id and Type """
        resp = self.app.get('/recommendations?product_id=10&type=up-sell')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(json.loads(resp.data)), 1)

    def test_get_recommendation(self):
        """ Get one Recommendation """
        resp = self.app.get('/recommendations/2')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = json.loads(resp.data)

        self.assertEqual(data['id'], 2)
        self.assertEqual(data['product_id'], 20)
        self.assertEqual(data['rec_type_id'], 2)

    def test_get_recommendation_not_found(self):
        """ Get a Recommendation thats not found """
        resp = self.app.get('/recommendations/0')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_recommendation_when_no_data_exist(self):
        """ Get a Recommendation thats not found when there is no data """
        RecommendationDetail.remove_all()
        Recommendation.remove_all()
        resp = self.app.get('/recommendations/0')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_rating_recommendation(self):
        """ Rating of Recommendation """
        resp = self.app.get('/recommendations/rating')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data, '2.5')

    def test_create_recommendation(self):
        """ Create a Recommendation """
        # save the current number of recommendations for later comparrison
        recommendation_count = self.get_recommendation_count()

        # add a new recommendation
        new_recommendation = {'product_id': 20, 'type': 'up-sell'}
        data_obj = json.dumps(new_recommendation)

        resp = self.app.post('/recommendations', data=data_obj, content_type='application/json')
        
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

        # Make sure location header is set
        location = resp.headers.get('Location', None)
        self.assertIsNotNone(location)

        # Check the data is correct
        new_json = json.loads(resp.data)

        self.assertEqual(new_json['product_id'], 20)

        # check that count has gone up and includes sammy
        resp = self.app.get('/recommendations')
        data = json.loads(resp.data)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(data), recommendation_count + 1)
        self.assertIn(new_json, data)

    def test_update_recommendation(self):
        """ Update a Recommendation """
        rec_changes = {'product_id': 21, 'type': 'cross-sell'}
        data = json.dumps(rec_changes)
        resp = self.app.put('/recommendations/2', data=data, content_type='application/json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        resp = self.app.get('/recommendations/2', content_type='application/json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        new_json = json.loads(resp.data)
        self.assertEqual(new_json['product_id'], 21)

    def test_update_recommendation_not_found(self):
        """ Update a Recommendation that can't be found """
        new_recommendation = {'product_id': 21, 'rec_type_id': 3}
        data = json.dumps(new_recommendation)
        resp = self.app.put('/recommendations/0', data=data, content_type='application/json')
        self.assertEquals(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_dislike_recommendation(self):
        """ Dislike a Recommendation """

        resp = self.app.get('/recommendations')
        data = json.loads(resp.data)
        rec_id = data[0]['rec_type_id']
        product_id = data[0]['recommendations'][0]['rec_product_id']
        dislike_count = data[0]['recommendations'][0]['dislike_count']

        resp = self.app.put('/recommendations/%i/%i/dislike' % (rec_id, product_id), content_type='application/json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        resp = self.app.get('/recommendations/%i' % rec_id, content_type='application/json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        new_json = json.loads(resp.data)
        self.assertEqual(new_json['recommendations'][0]['dislike_count'], dislike_count + 1)

    # TODO: This might not be applicable
    # def test_dislike_recommendation_with_deletion(self):
    #     """ Delete a Recommendation that is disliked """
    #      # save the current number of recommendations for later comparrison
    #     recommendation_count = self.get_recommendation_count()
    #
    #     new_recommendation = {}
    #     data = json.dumps(new_recommendation)
    #     resp = self.app.put('/recommendations/3/dislike', data=data, content_type='application/json')
    #     self.assertEqual(resp.status_code, status.HTTP_200_OK)
    #     # Since dislikes count reached the threshold (5), recommendation with id 3 is deleted
    #     # Hence get(/recommendations/3) must return 404 NOT FOUND
    #     resp = self.app.get('/recommendations/3', content_type='application/json')
    #     self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
    #     self.assertTrue(len(resp.data) > 0)
    #     new_count = self.get_recommendation_count()
    #     self.assertEqual(new_count, recommendation_count - 1)

    def test_dislike_recommendation_not_found(self):
        """ Dislike a Recommendation that can't be found"""

        resp = self.app.put('/recommendations/0/dislike', content_type='application/json')
        self.assertEquals(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_recommendation(self):
        """ Delete a Recommendation that exists """
        # save the current number of recommendations for later comparrison
        recommendation_count = self.get_recommendation_count()

        resp = self.app.get('/recommendations')
        data = json.loads(resp.data)
        rec_id = data[0]['rec_type_id']

        # delete a recommendation
        resp = self.app.delete('/recommendations/%i' % rec_id, content_type='application/json')
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(len(resp.data), 0)
        new_count = self.get_recommendation_count()
        resp = self.app.get('/recommendations/%i' % rec_id)
        self.assertEqual(new_count, recommendation_count - 1)

    def test_get_nonexisting_recommendation(self):
        """ Get a Recommendation that doesn't exist """
        resp = self.app.get('/recommendations/0')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_query_recommendation_by_type(self):
        """ Query Recommendation by Category """
        resp = self.app.get('/recommendations', query_string='type=up-sell')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(len(resp.data) > 0)
        data = json.loads(resp.data)[0]
        self.assertTrue('up-sell' in data['rec_type']['name'])

    def test_get_query_with_unknown_type(self):
        """ Get a Recommendation that doesn't exist by type """
        resp = self.app.get('/recommendations', query_string='type=milk')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_query_recommendation_when_no_data_exist(self):
        """ Get a Recommendation thats not found """
        db.drop_all()
        db.create_all()
        resp = self.app.get('/recommendations', query_string='type=milk')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_method_not_allowed(self):
        """ Call a Method thats not Allowed """
        resp = self.app.post('/recommendations/0')
        self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    @patch('server.Recommendation.find_by_product_id_and_type')
    def test_bad_data_request(self, bad_request_mock):
        """ Test a Bad Request error from Find By Type """
        bad_request_mock.side_effect = ValueError()
        resp = self.app.get('/recommendations', query_string='type=accessory&product_id=32')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_bad_post_request(self):
        """ Test a Validation error when performing a POST """
        new_recommendation = {'id': 87}
        data = json.dumps(new_recommendation)
        resp = self.app.post('/recommendations', data=data, content_type='application/json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    @mock.patch('server.Recommendation.find_by_product_id_and_type')
    def test_search_bad_data(self, recommendation_find_mock):
        """ Test a search that returns bad data """
        recommendation_find_mock.return_value = 4
        resp = self.app.get('/recommendations', query_string='type=up-sell&product_id=1')
        self.assertEqual(resp.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

######################################################################
# Utility functions
######################################################################

    def get_recommendation_count(self):
        """ save the current number of recommendations """
        resp = self.app.get('/recommendations')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = json.loads(resp.data)
        return len(data)


######################################################################
#   M A I N
######################################################################
if __name__ == '__main__':
    unittest.main()

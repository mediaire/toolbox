import unittest

from mediaire_toolbox.transaction_db.user_service import UserService
from mediaire_toolbox.transaction_db.transaction_db import TransactionDB

from temp_db_base import TempDBFactory

temp_db = TempDBFactory('test_user_service')


class TestUserService(unittest.TestCase):
        
    def test_permission_mask_to_id_set(self):
        set_ = UserService.permission_mask_to_id_set(130)
        self.assertEqual(2, len(set_))
        self.assertTrue(1 in set_)
        self.assertTrue(7 in set_)
        set_ = UserService.permission_mask_to_id_set(16)
        self.assertEqual(1, len(set_))
        self.assertTrue(4 in set_)

    def test_permission_set_to_mask(self):
        set_ = set([1, 7])
        self.assertEqual(130, UserService.permission_set_to_mask(set_))
        set_ = set([4])
        self.assertEqual(16, UserService.permission_set_to_mask(set_))

    def test_get_user_roles(self):
        engine = temp_db.get_temp_db()
        t_db = TransactionDB(engine)
        user_id = t_db.add_user('Pere', 'pwd')
        t_db.add_role('radiologist', 'whatever', 130)
        t_db.add_role('mediaire_tester', 'whatever', 16)

        t_db.add_user_role(user_id, 'radiologist')
        t_db.add_user_role(user_id, 'mediaire_tester')
        
        user_service = UserService(t_db)
        role_ids = set([r.role_id for r in \
                        user_service.get_user_roles('Pere')])
        self.assertEqual(2, len(role_ids))        
        self.assertTrue('radiologist' in role_ids)
        self.assertTrue('mediaire_tester' in role_ids)
            
    def test_get_user_permissions(self):
        engine = temp_db.get_temp_db()
        t_db = TransactionDB(engine)
        user_id = t_db.add_user('Pere', 'pwd')
        t_db.add_role('radiologist', 'whatever', 130)
        t_db.add_role('mediaire_tester', 'whatever', 16)

        t_db.add_user_role(user_id, 'radiologist')
        t_db.add_user_role(user_id, 'mediaire_tester')
        
        user_service = UserService(t_db)
        p_mask = user_service.get_user_permissions('Pere')
        p_set = UserService.permission_mask_to_id_set(p_mask)
        
        self.assertEqual(3, len(p_set))
        self.assertTrue(1 in p_set)
        self.assertTrue(4 in p_set)
        self.assertTrue(7 in p_set)
            

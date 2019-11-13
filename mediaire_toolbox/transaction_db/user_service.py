from mediaire_toolbox.transaction_db.transaction_db import TransactionDB

from mediaire_toolbox.transaction_db.model import User, UserRole, Role

class UserService:
    """Higher level service that uses the TransactionDB for operations related
    to User management"""
    
    def __init__(self, t_db: TransactionDB):
        self.t_db = t_db
        
    def get_user_by_name(self, name):
        return self.t_db.session.query(User).filter_by(name=name).first()
        
    def get_user_roles(self, username):
        user = self.get_user_by_name(username)
        return list(self.t_db.session.query(UserRole)\
                                     .filter_by(user_id=user.id))
        
    def get_user_permissions(self, username: str) -> int:
        """Returns the permission mask associated with this User.
        Each bit in the mask represents a different permission.
        The set of permissions can be obtained via the helper method
        permission_mask_to_id_set()"""
        permissions = 0        
        for role in self.get_user_roles(username):
            the_role = self.t_db.session.query(Role).get(role.role_id)
            permissions |= the_role.permissions
        return permissions
    
    @staticmethod
    def permission_set_to_mask(permission_set: set) -> int:
        """Create an int permission mask from a set of permission ids (ints) 
        """
        permissions_mask = 0
        for permission in permission_set: 
            permissions_mask |= 2**permission
        return permissions_mask
            
    @staticmethod
    def permission_mask_to_id_set(permissions: int) -> set:
        """Create an int permission ids set from a permission mask"""
        id_set = set()
        for i in range(0, 4*8):
            if permissions & 2**i:
                id_set.add(i)
        return id_set
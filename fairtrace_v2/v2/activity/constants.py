# Activity types
USER_UPDATED_EMAIL = 1
USER_LOGGED_IN_FROM_NEW_DEVICE = 2
USER_GENERATED_MAGIC_LINK_TO_LOGIN = 3
USER_UPDATED_PROFILE_IMAGE = 4
USER_CHANGED_PASSWORD = 5
USER_RESET_PASSWORD = 6
USER_CREATED_COMPANY = 7
UPDATED_NODE_DETAILS = 8
ADDED_AS_MEMBER = 9
REMOVED_MEMBER = 25
USER_MADE_ADMIN = 26
USER_MADE_MEMBER = 27
USER_MADE_VIEWER = 56
ADDED_NODE_DOCUMENT = 10
DELETED_NODE_DOCUMENT = 11
NODE_INVITED_NODE = 12
NODE_RECEIVED_INVITATION = 13
NODE_SENT_STOCK = 14
NODE_RECEIVED_STOCK = 15
NODE_USER_INTERNAL_TRANSACTION = 16
NODE_SYSTEM_INTERNAL_TRANSACTION = 17
NODE_USER_REJECTED_TRANSACTION = 18
NODE_STOCK_WAS_RETURNED = 19
NODE_USER_ADDED_COMMENT_TO_BATCH = 20
NODE_CREATED_STOCK_REQUEST = 21
NODE_RECEIVED_STOCK_REQUEST = 22
NODE_RECEIVED_INVITATION_FROM_FFADMIN = 57
NODE_DECLINED_STOCK_REQUEST = 30
STOCK_REQUEST_WAS_DECLINED = 31
NODE_CREATED_CLAIM_REQUEST = 39
NODE_RECEIVED_CLAIM_REQUEST = 40
NODE_DECLINED_CLAIM_REQUEST = 41
CLAIM_REQUEST_WAS_DECLINED = 42
NODE_CREATED_INFORMATION_REQUEST = 43
NODE_RECEIVED_INFORMATION_REQUEST = 44
NODE_DECLINED_INFORMATION_REQUEST = 45
INFORMATION_REQUEST_WAS_DECLINED = 46
NODE_CREATED_CONNECTION_REQUEST = 47
NODE_RECEIVED_CONNECTION_REQUEST = 48
CONNECTION_REQUEST_WAS_DECLINED = 49
NODE_DECLINED_CONNECTION_REQUEST = 50
INFORMATION_RECEIVED_RESPONSE = 51
NODE_RESPOND_INFORMATION_REQUEST = 52
CLAIM_RECEIVED_RESPONSE = 53
NODE_RESPOND_CLAIM_REQUEST = 54
NODE_USER_ATTACHED_CLAIM_TO_BATCH = 23
NODE_ATTACHED_CLAIM_TO_TRANSACTION = 24
NODE_SENT_VERIFICATION_REQUEST = 28
NODE_RECEIVED_VERIFICATION_REQUEST = 29
VERIFIER_APPROVED_CLAIM = 32
NODE_CLAIM_APPROVED = 33
VERIFIER_REJECTED_CLAIM = 34
NODE_CLAIM_REJECTED = 35
SENT_COMMENT_ON_CLAIM = 36
RECEIVED_COMMENT_ON_CLAIM = 37
NODE_ADDED_COMPANY_CLAIM = 38
FFADMIN_INVITED_COMPANY = 55
NODE_JOINED_FFADMIN_INVITE = 58
FARMER_CREATED = 59
FARMER_EDITED = 60
CARD_ADDED = 61
CARD_REMOVED = 62
# Max value : 62

ACTIVITY_TYPE_CHOICES = (
    (USER_UPDATED_EMAIL, "User Updated Email"),
    (USER_LOGGED_IN_FROM_NEW_DEVICE, "User Logged In From New Device"),
    (USER_GENERATED_MAGIC_LINK_TO_LOGIN, "User Generated Magic Link To Login"),
    (USER_UPDATED_PROFILE_IMAGE, "User Updated Profile Image"),
    (USER_CHANGED_PASSWORD, "User Changed Password"),
    (USER_RESET_PASSWORD, "User Reset Password"),
    (USER_CREATED_COMPANY, "User Created Company"),
    (UPDATED_NODE_DETAILS, "Updated Node Details"),
    (ADDED_AS_MEMBER, "Added As Member"),
    (REMOVED_MEMBER, "Member Removed"),
    (USER_MADE_ADMIN, "User was made Admin"),
    (USER_MADE_MEMBER, "User was made Member"),
    (USER_MADE_VIEWER, "User was made Viewer"),
    (ADDED_NODE_DOCUMENT, "Added Node Document"),
    (DELETED_NODE_DOCUMENT, "Deleted Node Document"),
    (NODE_INVITED_NODE, "Node Invited Node"),
    (NODE_RECEIVED_INVITATION, "Node Received Invitation"),
    (FFADMIN_INVITED_COMPANY, "Node Invited FFAdmin"),
    (
        NODE_RECEIVED_INVITATION_FROM_FFADMIN,
        "Node Received FFAdmin Invitation",
    ),
    (NODE_SENT_STOCK, "Node Sent Stock"),
    (NODE_RECEIVED_STOCK, "Node Received Stock"),
    (NODE_USER_INTERNAL_TRANSACTION, "Node User Internal Transaction"),
    (NODE_SYSTEM_INTERNAL_TRANSACTION, "Node System Internal Transaction"),
    (NODE_USER_REJECTED_TRANSACTION, "Node User Rejected Transaction"),
    (NODE_STOCK_WAS_RETURNED, "Node Stock Was Returned"),
    (NODE_USER_ADDED_COMMENT_TO_BATCH, "Node User Added Comment To Batch"),
    (NODE_CREATED_STOCK_REQUEST, "Node Created Stock Request"),
    (NODE_RECEIVED_STOCK_REQUEST, "Node Received Stock Request"),
    (NODE_DECLINED_STOCK_REQUEST, "Declined stock request"),
    (STOCK_REQUEST_WAS_DECLINED, "Stock request was declined"),
    (NODE_CREATED_CLAIM_REQUEST, "Node Created Claim Request"),
    (NODE_RECEIVED_CLAIM_REQUEST, "Node Received Claim Request"),
    (NODE_DECLINED_CLAIM_REQUEST, "Declined claim request"),
    (CLAIM_REQUEST_WAS_DECLINED, "Claim request was declined"),
    (NODE_CREATED_INFORMATION_REQUEST, "Node Created Information Request"),
    (NODE_RECEIVED_INFORMATION_REQUEST, "Node Received Information Request"),
    (NODE_DECLINED_INFORMATION_REQUEST, "Declined information request"),
    (INFORMATION_REQUEST_WAS_DECLINED, "Information request was declined"),
    (NODE_CREATED_CONNECTION_REQUEST, "Node Created Connection Request"),
    (NODE_RECEIVED_CONNECTION_REQUEST, "Node Received Connection Request"),
    (NODE_USER_ATTACHED_CLAIM_TO_BATCH, "Node User Attached Claim To Batch"),
    (NODE_ATTACHED_CLAIM_TO_TRANSACTION, "Node Attached Claim To Transaction"),
    (NODE_SENT_VERIFICATION_REQUEST, "Sent verification request."),
    (NODE_RECEIVED_VERIFICATION_REQUEST, "Received verification request"),
    (VERIFIER_APPROVED_CLAIM, "Approved Claims"),
    (NODE_CLAIM_APPROVED, "Claim was approved"),
    (VERIFIER_REJECTED_CLAIM, "Rejected claim"),
    (NODE_CLAIM_REJECTED, "Claim was rejected"),
    (SENT_COMMENT_ON_CLAIM, "Sent comment"),
    (RECEIVED_COMMENT_ON_CLAIM, "Received comment"),
    (NODE_ADDED_COMPANY_CLAIM, "Node Added Company Claim"),
    (NODE_DECLINED_CONNECTION_REQUEST, "Declined connection request"),
    (INFORMATION_RECEIVED_RESPONSE, "Received information response"),
    (NODE_RESPOND_INFORMATION_REQUEST, "Node added information response"),
    (CLAIM_RECEIVED_RESPONSE, "Received claim response"),
    (NODE_RESPOND_CLAIM_REQUEST, "Node added claim response"),
    (NODE_JOINED_FFADMIN_INVITE, "Node joined FFAdmin Invitation"),
    (FARMER_CREATED, "Farmer created by a manager company"),
    (FARMER_CREATED, "Farmer created by a manager company"),
    (CARD_ADDED, "Card issued to a farmer"),
    (CARD_REMOVED, "Card removed from a farmer"),
)

# Object types
OBJECT_TYPE_USER = 1
OBJECT_TYPE_VALIDATION_TOKEN = 2
OBJECT_TYPE_NODE = 3
OBJECT_TYPE_NODE_MEMBER = 4
OBJECT_TYPE_NODE_DOCUMENT = 5
OBJECT_TYPE_INVITATION = 6
OBJECT_TYPE_EXT_TRANSACTION = 7
OBJECT_TYPE_INT_TRANSACTION = 8
OBJECT_TYPE_ATTACHED_CLAIM = 9
OBJECT_TYPE_BATCH_COMMENT = 10
OBJECT_TYPE_TRANSACTION_CLAIM = 12
OBJECT_TYPE_CLAIM_COMMENT = 13
OBJECT_TYPE_TRANSACTION_REQUEST = 11
OBJECT_TYPE_CLAIM_REQUEST = 14
OBJECT_TYPE_INFORMATION_REQUEST = 15
OBJECT_TYPE_CONNECTION_REQUEST = 16
OBJECT_TYPE_FFADMIN_INVITATION = 17
OBJECT_TYPE_NODE_CARD_HISTORY = 18

OBJECT_TYPE_CHOICES = (
    (OBJECT_TYPE_USER, "User"),
    (OBJECT_TYPE_VALIDATION_TOKEN, "Validation Token"),
    (OBJECT_TYPE_NODE, "Node"),
    (OBJECT_TYPE_NODE_MEMBER, "Node Member"),
    (OBJECT_TYPE_NODE_DOCUMENT, "Node Document"),
    (OBJECT_TYPE_INVITATION, "Invitation"),
    (OBJECT_TYPE_EXT_TRANSACTION, "External Transaction"),
    (OBJECT_TYPE_INT_TRANSACTION, "Internal Transaction"),
    (OBJECT_TYPE_ATTACHED_CLAIM, "Attached Claim"),
    (OBJECT_TYPE_BATCH_COMMENT, "Batch Comment"),
    (OBJECT_TYPE_TRANSACTION_CLAIM, "Transaction Claim"),
    (OBJECT_TYPE_TRANSACTION_REQUEST, "Transaction Request"),
    (OBJECT_TYPE_CLAIM_REQUEST, "Claim Request"),
    (OBJECT_TYPE_INFORMATION_REQUEST, "Information Request"),
    (OBJECT_TYPE_CONNECTION_REQUEST, "Connection Request"),
    (OBJECT_TYPE_FFADMIN_INVITATION, "FFAdmin Invitation"),
    (OBJECT_TYPE_CLAIM_COMMENT, "Claim Comment"),
    (OBJECT_TYPE_NODE_CARD_HISTORY, "Node Card History"),
)

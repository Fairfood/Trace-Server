"""URLs of the app accounts."""
from django.urls import include
from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import admin_dashboard as ffadmin_views
from .views import admin_dashboard_v3 as ff_admin_views_v3
from .views import node as node_views
from .views import other as other_views
from .views import supply_chain as sc_views

router = DefaultRouter()
router.register(
    "country-node-count",
    ff_admin_views_v3.CountryNodeCountViewSet,
    base_name="country-node-count",
)
router.register(
    "farmers", ff_admin_views_v3.AdminFarmerViewSet, base_name="farmers"
)
router.register(
    "companies", ff_admin_views_v3.AdminCompanyViewSet, base_name="companies"
)
router.register(
    "node-count",
    ff_admin_views_v3.AdminNodeCountViewSet,
    base_name="node-count",
)

default_router = DefaultRouter()
default_router.register(
    "references", other_views.ReferenceViewSet, base_name="references"
)
default_router.register(
    "farmer-references",
    other_views.FarmerReferenceViewSet,
    base_name="farmer-references",
)
default_router.register(
    "farmer-plots", other_views.FarmerPlotViewSet, base_name="farmer-plots"
)
default_router.register(
    "farmer-attachments",
    other_views.FarmerAttachmentViewSet,
    base_name="farmer-attachments",
)
default_router.register(
    "connection-nodes",
    sc_views.ConnectionNodeViewSet,
    base_name="connection-nodes",
)

urlpatterns = [
    # Node
    path(
        "validate/company-name/",
        node_views.ValidateCompanyName.as_view(),
        name="validate_company_name",
    ),
    path("farmer/", node_views.FarmerView.as_view(), name="farmer"),
    path("company/", node_views.CompanyView.as_view(), name="company"),
    path(
        "operations/", node_views.OperationsList.as_view(), name="operations"
    ),
    path(
        "connections/", node_views.MyConnections.as_view(), name="connections"
    ),
    path(
        "farmer/<idencode:pk>/",
        node_views.FarmerDetails.as_view(),
        name="farmer-details",
    ),
    path(
        "company/<idencode:pk>/",
        node_views.CompanyDetails.as_view(),
        name="company-details",
    ),
    path(
        "validate/farmer/",
        node_views.ValidateFarmerID.as_view(),
        name="validate_farmer",
    ),
    path(
        "node/member/",
        node_views.CreateListNodeMember.as_view(),
        name="node-member",
    ),
    path(
        "node/member/<idencode:pk>/resend/",
        node_views.ResendNodeMemberInvite.as_view(),
        name="resend-node-member",
    ),
    path(
        "node/member/<idencode:pk>/",
        node_views.GetUpdateRemoveNodeMember.as_view(),
        name="update-remove-node-member",
    ),
    path(
        "node/documents/",
        node_views.AddListNodeDocument.as_view(),
        name="node-document",
    ),
    path(
        "node/documents/<idencode:pk>/",
        node_views.DeleteNodeDocument.as_view(),
        name="remove-node-document",
    ),
    path(
        "managed/farmers/",
        node_views.ManagedFarmers.as_view(),
        name="managed-farmers",
    ),
    path(
        "node/wallet/",
        node_views.ListNodeWallets.as_view(),
        name="node-wallets",
    ),
    # Supply chain
    path("", sc_views.SupplyChainList.as_view(), name="supply-chain"),
    path(
        "farmer/bulk/",
        sc_views.FarmerBulkInviteUpdate.as_view(),
        name="farmer-bulk",
    ),
    path(
        "invite/company/",
        sc_views.InviteCompany.as_view(),
        name="invite-company",
    ),
    path(
        "invite/farmer/", sc_views.InviteFarmer.as_view(), name="invite-farmer"
    ),
    path(
        "invitation/resend/",
        sc_views.ResendInvite.as_view(),
        name="resend-invitation",
    ),
    path(
        "connections/<idencode:pk>/map/",
        sc_views.MapConnectionView.as_view(),
        name="map-connections",
    ),
    path(
        "connections/<idencode:pk>/table/",
        sc_views.TableConnectionView.as_view(),
        name="table-connections",
    ),
    path(
        "connection/tag/<idencode:pk>/",
        sc_views.UpdateTag.as_view(),
        name="tag-connection",
    ),
    path(
        "connection/search/<idencode:pk>/",
        sc_views.SearchNode.as_view(),
        name="connection-search",
    ),
    path("suppliers/", sc_views.GetSuppliers.as_view(), name="suppliers"),
    path("buyers/", sc_views.GetBuyers.as_view(), name="buyers"),
    path("products/", sc_views.ProductView.as_view()),
    # Labels
    path("label/", sc_views.LabelsAPI.as_view(), name="label"),
    path(
        "label/<idencode:pk>/",
        sc_views.RetrieveUpdateDestroyLabels.as_view(),
        name="labels",
    ),
    path(
        "connection/label/<idencode:pk>/",
        sc_views.UpdateConnectionLabel.as_view(),
        name="connection-label",
    ),
    path(
        "bulk/farmer/",
        sc_views.FarmerTemplate.as_view(),
        name="farmer-template",
    ),
    path(
        "node-supplychain/<idencode:pk>/",
        sc_views.RemoveNodeSupplyChain.as_view(),
        name="node-supply_chain",
    ),
    path(
        "select/<idencode:pk>/",
        sc_views.SupplyChainActive.as_view(),
        name="supply_chain-active",
    ),
    # Static data
    path("countries/", other_views.CountryData.as_view(), name="countries"),
    # FFAdmin Company
    path(
        "admin/",
        ffadmin_views.FFAdminSupplyChainList.as_view(),
        name="admin-supplychain",
    ),
    path(
        "admin/company/",
        ffadmin_views.FFAdminCompanyView.as_view(),
        name="admin-company",
    ),
    path(
        "admin/company/<idencode:pk>/",
        ffadmin_views.FFAdminCompanyDetails.as_view(),
        name="admin-company-details",
    ),
    path(
        "admin/invite/company/",
        ffadmin_views.FFAdminInviteCompany.as_view(),
        name="admin-invite-company",
    ),
    path(
        "admin/company/<idencode:pk>/member/",
        ffadmin_views.FFAdminNodeMemberView.as_view(),
        name="admin-company-member",
    ),
    path(
        "admin/company/member/<idencode:pk>/",
        ffadmin_views.FFAdminNodeMemberDetailsView.as_view(),
        name="admin-member-details",
    ),
    path(
        "admin/company/member/<idencode:pk>/resend/",
        ffadmin_views.FFAdminResendNodeMemberInvite.as_view(),
        name="admin-resend-nodemember",
    ),
    path(
        "admin/company/activity/<idencode:pk>/",
        ffadmin_views.FFAdminCompanyActivity.as_view(),
        name="admin-company-activity",
    ),
    path(
        "admin/node-supplychain/<idencode:pk>/",
        sc_views.AddNodeSupplyChains.as_view(),
        name="admin-node-supplychain",
    ),
    path(
        "admin/supplychain/node/<idencode:pk>/",
        sc_views.NodeSupplyChains.as_view(),
        name="admin-node-supplychain-list",
    ),
    # FFAdmin SupplyChain
    path(
        "admin/supplychain/",
        ffadmin_views.FFAdminSupplyChainView.as_view(),
        name="admin-supply-chain",
    ),
    path(
        "admin/supplychain/<idencode:pk>/",
        ffadmin_views.UpdateSupplyChain.as_view(),
        name="admin-supply-chain-update",
    ),
    path(
        "admin/invitation/resend/<idencode:pk>/",
        ffadmin_views.FFAdminResendInvite.as_view(),
        name="admin-invitation-resend",
    ),
    # FFAdmin product
    path(
        "admin/products/",
        ffadmin_views.FFAdminProductView.as_view(),
        name="admin-products",
    ),
    path(
        "admin/products/<idencode:pk>/",
        ffadmin_views.FFAdminUpdateProduct.as_view(),
        name="admin-product-update",
    ),
    # FFAdmin theme
    path(
        "admin/theme/node/<idencode:pk>/",
        ffadmin_views.FFAdminNodeThemeView.as_view(),
        name="admin-node-theme",
    ),
    path(
        "admin/verifier/<idencode:pk>/",
        ffadmin_views.FFAdminNodeVerifier.as_view(),
        name="admin-verifier",
    ),
    # FF-Admin V3
    path("admin/", include(router.urls)),
    path("supply-chains/", include(default_router.urls)),
    path(
        "carbon-connections/", 
        sc_views.CarbonConnectionView.as_view(),
        name="carbon-connections"
    )
]

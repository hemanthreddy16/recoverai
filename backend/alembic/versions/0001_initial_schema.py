"""Initial schema migration for Resurge.

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-08-26 20:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. merchants
    op.create_table(
        'merchants',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('slug', sa.String(length=200), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug')
    )

    # 2. users
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('merchant_id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=200), nullable=False, server_default=''),
        sa.Column('role', sa.String(length=50), nullable=False, server_default='operator'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['merchant_id'], ['merchants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_index(op.f('ix_users_merchant_id'), 'users', ['merchant_id'], unique=False)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # 3. customers
    op.create_table(
        'customers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('merchant_id', sa.Integer(), nullable=False),
        sa.Column('external_id', sa.String(length=200), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False, server_default=''),
        sa.Column('email', sa.String(length=255), nullable=False, server_default=''),
        sa.Column('phone', sa.String(length=50), nullable=False, server_default=''),
        sa.Column('clv', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['merchant_id'], ['merchants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_customers_merchant_id'), 'customers', ['merchant_id'], unique=False)
    op.create_index(op.f('ix_customers_external_id'), 'customers', ['external_id'], unique=False)

    # 4. orders
    op.create_table(
        'orders',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('merchant_id', sa.Integer(), nullable=False),
        sa.Column('customer_id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('currency', sa.String(length=10), nullable=False, server_default='INR'),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='created'),
        sa.Column('abandoned_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['merchant_id'], ['merchants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_orders_merchant_id'), 'orders', ['merchant_id'], unique=False)
    op.create_index(op.f('ix_orders_customer_id'), 'orders', ['customer_id'], unique=False)

    # 5. subscriptions
    op.create_table(
        'subscriptions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('merchant_id', sa.Integer(), nullable=False),
        sa.Column('customer_id', sa.Integer(), nullable=False),
        sa.Column('plan', sa.String(length=120), nullable=False, server_default='default'),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('currency', sa.String(length=10), nullable=False, server_default='INR'),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='active'),
        sa.Column('failure_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('current_period_end', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['merchant_id'], ['merchants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_subscriptions_merchant_id'), 'subscriptions', ['merchant_id'], unique=False)
    op.create_index(op.f('ix_subscriptions_customer_id'), 'subscriptions', ['customer_id'], unique=False)

    # 6. payments
    op.create_table(
        'payments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('merchant_id', sa.Integer(), nullable=False),
        sa.Column('customer_id', sa.Integer(), nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=True),
        sa.Column('subscription_id', sa.Integer(), nullable=True),
        sa.Column('razorpay_payment_id', sa.String(length=200), nullable=True),
        sa.Column('razorpay_order_id', sa.String(length=200), nullable=True),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('currency', sa.String(length=10), nullable=False, server_default='INR'),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('failure_reason', sa.String(length=120), nullable=True),
        sa.Column('payment_method', sa.String(length=60), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('captured_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['merchant_id'], ['merchants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['subscription_id'], ['subscriptions.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_payments_merchant_id'), 'payments', ['merchant_id'], unique=False)
    op.create_index(op.f('ix_payments_customer_id'), 'payments', ['customer_id'], unique=False)
    op.create_index(op.f('ix_payments_status'), 'payments', ['status'], unique=False)
    op.create_index(op.f('ix_payments_razorpay_payment_id'), 'payments', ['razorpay_payment_id'], unique=False)
    op.create_index(op.f('ix_payments_razorpay_order_id'), 'payments', ['razorpay_order_id'], unique=False)

    # 7. revenue_events
    op.create_table(
        'revenue_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('merchant_id', sa.Integer(), nullable=False),
        sa.Column('customer_id', sa.Integer(), nullable=True),
        sa.Column('payment_id', sa.Integer(), nullable=True),
        sa.Column('event_type', sa.String(length=80), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('currency', sa.String(length=10), nullable=False, server_default='INR'),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='received'),
        sa.Column('razorpay_event_id', sa.String(length=200), nullable=True),
        sa.Column('payload', sa.Text(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['merchant_id'], ['merchants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['payment_id'], ['payments.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('razorpay_event_id', name='uq_revenue_event_id')
    )
    op.create_index(op.f('ix_revenue_events_merchant_id'), 'revenue_events', ['merchant_id'], unique=False)
    op.create_index(op.f('ix_revenue_events_event_type'), 'revenue_events', ['event_type'], unique=False)

    # 8. recovery_cases
    op.create_table(
        'recovery_cases',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('merchant_id', sa.Integer(), nullable=False),
        sa.Column('customer_id', sa.Integer(), nullable=False),
        sa.Column('payment_id', sa.Integer(), nullable=True),
        sa.Column('order_id', sa.Integer(), nullable=True),
        sa.Column('subscription_id', sa.Integer(), nullable=True),
        sa.Column('amount_at_risk', sa.Float(), nullable=False),
        sa.Column('risk_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('event_type', sa.String(length=60), nullable=False),
        sa.Column('failure_reason', sa.String(length=120), nullable=True),
        sa.Column('detection_reason', sa.Text(), nullable=True),
        sa.Column('diagnosis', sa.Text(), nullable=True),
        sa.Column('diagnosis_confidence', sa.Float(), nullable=True),
        sa.Column('contributing_factors', sa.Text(), nullable=True),
        sa.Column('recommended_recovery_category', sa.String(length=60), nullable=True),
        sa.Column('recovery_probability', sa.Float(), nullable=True),
        sa.Column('model_version', sa.String(length=40), nullable=True),
        sa.Column('recommended_action', sa.String(length=60), nullable=True),
        sa.Column('strategy_rationale', sa.Text(), nullable=True),
        sa.Column('approved_action', sa.String(length=60), nullable=True),
        sa.Column('policy_decision', sa.String(length=40), nullable=True),
        sa.Column('policy_reason', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('max_attempts', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('action_status', sa.String(length=30), nullable=False, server_default='pending'),
        sa.Column('recovery_status', sa.String(length=30), nullable=False, server_default='open'),
        sa.Column('amount_recovered', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('assigned_to', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['merchant_id'], ['merchants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['payment_id'], ['payments.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['subscription_id'], ['subscriptions.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_recovery_cases_merchant_id'), 'recovery_cases', ['merchant_id'], unique=False)
    op.create_index(op.f('ix_recovery_cases_customer_id'), 'recovery_cases', ['customer_id'], unique=False)
    op.create_index(op.f('ix_recovery_cases_event_type'), 'recovery_cases', ['event_type'], unique=False)
    op.create_index(op.f('ix_recovery_cases_action_status'), 'recovery_cases', ['action_status'], unique=False)
    op.create_index(op.f('ix_recovery_cases_recovery_status'), 'recovery_cases', ['recovery_status'], unique=False)

    # 9. recovery_actions
    op.create_table(
        'recovery_actions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('merchant_id', sa.Integer(), nullable=False),
        sa.Column('case_id', sa.Integer(), nullable=False),
        sa.Column('action_type', sa.String(length=60), nullable=False),
        sa.Column('channel', sa.String(length=60), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='scheduled'),
        sa.Column('detail', sa.Text(), nullable=False, server_default='{}'),
        sa.Column('scheduled_time', sa.DateTime(), nullable=True),
        sa.Column('executed_at', sa.DateTime(), nullable=True),
        sa.Column('result', sa.Text(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['case_id'], ['recovery_cases.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['merchant_id'], ['merchants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_recovery_actions_merchant_id'), 'recovery_actions', ['merchant_id'], unique=False)
    op.create_index(op.f('ix_recovery_actions_case_id'), 'recovery_actions', ['case_id'], unique=False)

    # 10. agent_runs
    op.create_table(
        'agent_runs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('merchant_id', sa.Integer(), nullable=False),
        sa.Column('case_id', sa.Integer(), nullable=True),
        sa.Column('agent_name', sa.String(length=60), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='running'),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['case_id'], ['recovery_cases.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['merchant_id'], ['merchants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_runs_merchant_id'), 'agent_runs', ['merchant_id'], unique=False)
    op.create_index(op.f('ix_agent_runs_case_id'), 'agent_runs', ['case_id'], unique=False)
    op.create_index(op.f('ix_agent_runs_agent_name'), 'agent_runs', ['agent_name'], unique=False)

    # 11. agent_decisions
    op.create_table(
        'agent_decisions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('agent_run_id', sa.Integer(), nullable=False),
        sa.Column('case_id', sa.Integer(), nullable=True),
        sa.Column('merchant_id', sa.Integer(), nullable=False),
        sa.Column('agent_name', sa.String(length=60), nullable=False),
        sa.Column('decision_type', sa.String(length=80), nullable=False),
        sa.Column('input_data', sa.Text(), nullable=False, server_default='{}'),
        sa.Column('output_data', sa.Text(), nullable=False, server_default='{}'),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['agent_run_id'], ['agent_runs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['case_id'], ['recovery_cases.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['merchant_id'], ['merchants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_decisions_agent_run_id'), 'agent_decisions', ['agent_run_id'], unique=False)
    op.create_index(op.f('ix_agent_decisions_case_id'), 'agent_decisions', ['case_id'], unique=False)
    op.create_index(op.f('ix_agent_decisions_merchant_id'), 'agent_decisions', ['merchant_id'], unique=False)

    # 12. mcp_tool_calls
    op.create_table(
        'mcp_tool_calls',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('merchant_id', sa.Integer(), nullable=False),
        sa.Column('case_id', sa.Integer(), nullable=True),
        sa.Column('tool_name', sa.String(length=80), nullable=False),
        sa.Column('arguments', sa.Text(), nullable=False, server_default='{}'),
        sa.Column('result', sa.Text(), nullable=False, server_default='{}'),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='ok'),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('caller', sa.String(length=80), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['case_id'], ['recovery_cases.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['merchant_id'], ['merchants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_mcp_tool_calls_merchant_id'), 'mcp_tool_calls', ['merchant_id'], unique=False)
    op.create_index(op.f('ix_mcp_tool_calls_tool_name'), 'mcp_tool_calls', ['tool_name'], unique=False)

    # 13. notifications
    op.create_table(
        'notifications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('merchant_id', sa.Integer(), nullable=False),
        sa.Column('customer_id', sa.Integer(), nullable=True),
        sa.Column('case_id', sa.Integer(), nullable=True),
        sa.Column('channel', sa.String(length=40), nullable=False),
        sa.Column('subject', sa.String(length=255), nullable=False, server_default=''),
        sa.Column('body', sa.Text(), nullable=False, server_default=''),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='pending'),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['case_id'], ['recovery_cases.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['merchant_id'], ['merchants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_notifications_merchant_id'), 'notifications', ['merchant_id'], unique=False)

    # 14. audit_logs
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('merchant_id', sa.Integer(), nullable=False),
        sa.Column('actor', sa.String(length=80), nullable=False),
        sa.Column('action', sa.String(length=120), nullable=False),
        sa.Column('entity_type', sa.String(length=60), nullable=True),
        sa.Column('entity_id', sa.Integer(), nullable=True),
        sa.Column('detail', sa.Text(), nullable=False, server_default='{}'),
        sa.Column('ip_address', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['merchant_id'], ['merchants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_logs_merchant_id'), 'audit_logs', ['merchant_id'], unique=False)

    # 15. model_predictions
    op.create_table(
        'model_predictions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('merchant_id', sa.Integer(), nullable=False),
        sa.Column('case_id', sa.Integer(), nullable=True),
        sa.Column('payment_id', sa.Integer(), nullable=True),
        sa.Column('model_version', sa.String(length=40), nullable=False),
        sa.Column('features', sa.Text(), nullable=False, server_default='{}'),
        sa.Column('recovery_probability', sa.Float(), nullable=False),
        sa.Column('predicted_label', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['case_id'], ['recovery_cases.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['merchant_id'], ['merchants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['payment_id'], ['payments.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_model_predictions_merchant_id'), 'model_predictions', ['merchant_id'], unique=False)

    # 16. merchant_policies
    op.create_table(
        'merchant_policies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('merchant_id', sa.Integer(), nullable=False),
        sa.Column('automatic_threshold', sa.Float(), nullable=False, server_default='0.55'),
        sa.Column('approval_threshold', sa.Float(), nullable=False, server_default='0.4'),
        sa.Column('retry_limit', sa.Integer(), nullable=False, server_default='2'),
        sa.Column('max_recovery_attempts', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('high_value_threshold', sa.Float(), nullable=False, server_default='50000.0'),
        sa.Column('allow_auto_retry', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('allow_auto_payment_link', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('allow_auto_notification', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('notification_channels', sa.String(length=200), nullable=False, server_default='["email"]'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['merchant_id'], ['merchants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('merchant_id')
    )
    op.create_index(op.f('ix_merchant_policies_merchant_id'), 'merchant_policies', ['merchant_id'], unique=True)


def downgrade() -> None:
    op.drop_table('merchant_policies')
    op.drop_table('model_predictions')
    op.drop_table('audit_logs')
    op.drop_table('notifications')
    op.drop_table('mcp_tool_calls')
    op.drop_table('agent_decisions')
    op.drop_table('agent_runs')
    op.drop_table('recovery_actions')
    op.drop_table('recovery_cases')
    op.drop_table('revenue_events')
    op.drop_table('payments')
    op.drop_table('subscriptions')
    op.drop_table('orders')
    op.drop_table('customers')
    op.drop_table('users')
    op.drop_table('merchants')

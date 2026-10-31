from django.contrib.admin.models import LogEntry
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from orders.models import Cart, CartItem, Order, OrderStatusHistory
from products.models import Favorite, Review
from users.models import User
from users.utils import InvalidPhoneError, normalize_phone


class Command(BaseCommand):
    help = (
        'Safely merge two users with the same normalized phone. '
        'Dry-run by default; pass --commit to apply.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--primary', type=int, required=True)
        parser.add_argument('--duplicate', type=int, required=True)
        parser.add_argument('--commit', action='store_true')
        parser.add_argument(
            '--bonus',
            choices=('max', 'sum', 'primary', 'duplicate'),
            default='max',
            help='How to combine bonus_points (default: max).',
        )

    def handle(self, *args, **options):
        primary_id = options['primary']
        duplicate_id = options['duplicate']
        commit = options['commit']

        if primary_id == duplicate_id:
            raise CommandError('--primary and --duplicate must differ')

        try:
            primary = User.objects.get(pk=primary_id)
            duplicate = User.objects.get(pk=duplicate_id)
        except User.DoesNotExist as exc:
            raise CommandError(str(exc)) from exc

        try:
            primary_phone = normalize_phone(primary.phone)
            duplicate_phone = normalize_phone(duplicate.phone)
        except InvalidPhoneError as exc:
            raise CommandError(f'Cannot normalize phone: {exc}') from exc

        if primary_phone != duplicate_phone:
            raise CommandError(
                f'Phones differ: {primary_phone} != {duplicate_phone}. '
                'Refusing to merge different people.'
            )

        self.stdout.write('Users:')
        self.stdout.write(
            f'  primary   #{primary.id}: {primary.username} / {primary.phone} '
            f'/ {primary.full_name!r} / {primary.role} / {primary.bonus_points} бонусов'
        )
        self.stdout.write(
            f'  duplicate #{duplicate.id}: {duplicate.username} / {duplicate.phone} '
            f'/ {duplicate.full_name!r} / {duplicate.role} / {duplicate.bonus_points} бонусов'
        )

        counts = {
            'orders (user)': Order.objects.filter(user_id=duplicate.id).count(),
            'orders (courier)': Order.objects.filter(courier_id=duplicate.id).count(),
            'carts': Cart.objects.filter(user_id=duplicate.id).count(),
            'favorites': Favorite.objects.filter(user_id=duplicate.id).count(),
            'reviews': Review.objects.filter(user_id=duplicate.id).count(),
            'status history': OrderStatusHistory.objects.filter(
                changed_by_id=duplicate.id
            ).count(),
        }
        self.stdout.write('Related data on duplicate:')
        for label, count in counts.items():
            self.stdout.write(f'  {label}: {count}')

        if not commit:
            self.stdout.write(self.style.WARNING(
                'DRY RUN: no changes made. Re-run with --commit to merge.'
            ))
            return

        target_username = primary_phone
        username_taken = User.objects.exclude(
            pk__in=(primary.id, duplicate.id)
        ).filter(username=target_username).exists()
        if username_taken:
            raise CommandError(
                f'Username {target_username!r} is already used by another user'
            )

        with transaction.atomic():
            primary = User.objects.select_for_update().get(pk=primary.id)
            duplicate = User.objects.select_for_update().get(pk=duplicate.id)

            # Orders use PROTECT: move them before deleting the duplicate.
            Order.objects.filter(user_id=duplicate.id).update(user_id=primary.id)
            Order.objects.filter(courier_id=duplicate.id).update(courier_id=primary.id)
            OrderStatusHistory.objects.filter(
                changed_by_id=duplicate.id
            ).update(changed_by_id=primary.id)
            LogEntry.objects.filter(user_id=duplicate.id).update(user_id=primary.id)

            # Carts are OneToOne. Reassign if possible, otherwise merge items.
            primary_cart = Cart.objects.filter(user=primary).first()
            duplicate_cart = Cart.objects.filter(user=duplicate).first()
            if duplicate_cart:
                if primary_cart is None:
                    duplicate_cart.user = primary
                    duplicate_cart.save(update_fields=['user'])
                else:
                    for item in duplicate_cart.items.all():
                        target, created = CartItem.objects.get_or_create(
                            cart=primary_cart,
                            product=item.product,
                            variant=item.variant,
                            defaults={'quantity': item.quantity},
                        )
                        if not created:
                            target.quantity += item.quantity
                            target.save(update_fields=['quantity'])
                        item.delete()
                    duplicate_cart.delete()

            # Favorites are unique by (user, product).
            for favorite in Favorite.objects.filter(user=duplicate):
                Favorite.objects.get_or_create(
                    user=primary,
                    product=favorite.product,
                )
                favorite.delete()

            # Reviews are unique by (product, user). Keep the primary review
            # if both users reviewed the same product.
            for review in Review.objects.filter(user=duplicate):
                existing = Review.objects.filter(
                    user=primary,
                    product=review.product,
                ).first()
                if existing:
                    if not existing.text and review.text:
                        existing.text = review.text
                        existing.save(update_fields=['text'])
                    if review.is_approved and not existing.is_approved:
                        existing.is_approved = True
                        existing.save(update_fields=['is_approved'])
                    review.delete()
                else:
                    review.user = primary
                    review.save(update_fields=['user'])

            primary.groups.add(*duplicate.groups.all())
            primary.user_permissions.add(*duplicate.user_permissions.all())

            duplicate_bonus = duplicate.bonus_points
            if options['bonus'] == 'sum':
                bonus_points = primary.bonus_points + duplicate_bonus
            elif options['bonus'] == 'duplicate':
                bonus_points = duplicate_bonus
            elif options['bonus'] == 'primary':
                bonus_points = primary.bonus_points
            else:
                bonus_points = max(primary.bonus_points, duplicate_bonus)

            merged_fields = {
                'phone': primary_phone,
                'username': target_username,
                'full_name': primary.full_name or duplicate.full_name,
                'email': primary.email or duplicate.email,
                'fcm_token': primary.fcm_token or duplicate.fcm_token,
                'avatar': primary.avatar or duplicate.avatar,
                'birth_date': primary.birth_date or duplicate.birth_date,
                'bonus_points': bonus_points,
                'is_active': primary.is_active or duplicate.is_active,
                'date_joined': min(primary.date_joined, duplicate.date_joined),
                'last_login': max(
                    (value for value in (primary.last_login, duplicate.last_login)
                     if value is not None),
                    default=None,
                ),
            }

            # Delete duplicate first: its username/phone may equal the target.
            duplicate.delete()

            for field, value in merged_fields.items():
                setattr(primary, field, value)
            primary.save()

        self.stdout.write(self.style.SUCCESS(
            f'Merged user #{duplicate_id} into #{primary_id}; '
            f'phone={primary_phone}, username={target_username}.'
        ))
        self.stdout.write(self.style.WARNING(
            'Now run: python manage.py migrate users 0004 '
            '(preferred) or --fake if all phones were normalized manually.'
        ))

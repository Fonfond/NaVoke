from pathlib import Path

import pytest


def test_utils_loaded_before_admin():
    html = Path('frontend/pages/admin-panel.html').read_text(encoding='utf-8')
    assert html.index('/static/js/utils.js') < html.index('/static/js/admin.js')


def test_utils_loaded_before_order_detail():
    html = Path('frontend/pages/order-detail.html').read_text(encoding='utf-8')
    assert html.index('/static/js/utils.js') < html.index('/static/js/order-detail.js')


@pytest.mark.parametrize(
    ('page', 'scripts'),
    [
        ('catalog.html', ('cart.js', 'catalog.js')),
        ('cart.html', ('cart.js',)),
        ('checkout.html', ('cart.js', 'checkout.js')),
        ('product.html', ('cart.js', 'product.js')),
        ('profile.html', ('cart.js', 'profile.js')),
    ],
)
def test_utils_loaded_before_public_scripts(page, scripts):
    html = Path(f'frontend/pages/{page}').read_text(encoding='utf-8')
    utils_index = html.index('/static/js/utils.js')
    for script in scripts:
        assert utils_index < html.index(f'/static/js/{script}')


def test_escape_helper_covers_all_html_specials():
    source = Path('frontend/js/utils.js').read_text(encoding='utf-8')
    for char in ('&', '<', '>', '"', "'"):
        assert f"'{char}'" in source or f'"{char}"' in source


def test_no_token_logging_in_api():
    source = Path('frontend/js/api.js').read_text(encoding='utf-8')
    assert 'console.log(result.access' not in source
    assert 'console.log(result.refresh' not in source


def test_admin_js_uses_variant_detail_endpoint():
    source = Path('frontend/js/admin.js').read_text(encoding='utf-8')
    assert '/variants/delete/' not in source
    assert '/variants/${Number(variantId)}/' in source
    assert 'has_variants: hasVariants' in source
    assert 'editProductImageFile' in source
    assert 'uploadEditProductImage' in source


def test_external_cdn_scripts_are_deferred():
    for page in Path('frontend/pages').glob('*.html'):
        for line in page.read_text(encoding='utf-8').splitlines():
            if '<script' in line and 'cdn.jsdelivr.net' in line:
                assert 'defer' in line, f'Blocking CDN script in {page}: {line}'


@pytest.mark.parametrize(
    ('path', 'forbidden'),
    [
        (
            'frontend/js/product.js',
            (
                '${review.user_name',
                '${review.text',
                'class="product-title">${product.name}',
                'alt="${product.name}"',
                '${product.ingredients',
                '${product.description',
                '${v.name',
            ),
        ),
        (
            'frontend/js/catalog.js',
            (
                '${product.name}',
                '${product.ingredients',
                '${cat.name}',
                '${error.message}',
            ),
        ),
        (
            'frontend/js/cart.js',
            (
                '${item.product_name}',
                '${error.message}',
            ),
        ),
        (
            'frontend/js/checkout.js',
            (
                '${item.product_name}',
            ),
        ),
        (
            'frontend/js/profile.js',
            (
                '${order.order_number',
                '${item.product_name',
                '${productName}',
                'src="${productImage}"',
                '${error.message}',
                'status-${order.status',
            ),
        ),
    ],
)
def test_no_raw_api_interpolation_in_public_js(path, forbidden):
    source = Path(path).read_text(encoding='utf-8')
    for pattern in forbidden:
        assert pattern not in source, f'Unescaped interpolation {pattern!r} in {path}'

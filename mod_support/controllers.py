from flask import Blueprint, g

from decorators import get_menu_entries, template_renderer

mod_support = Blueprint('support', __name__)


@mod_support.before_app_request
def before_request():
    g.menu_entries['support'] = get_menu_entries(
        g.user, 'About & Help', 'question', '', [
            {'title': 'About', 'icon': 'info', 'route': 'support.about'},
            {'title': 'Support', 'icon': 'support', 'route':
                'support.support'}
        ]
    )


@mod_support.route('/about')
@template_renderer()
def about():
    return


@mod_support.route('/support')
@template_renderer()
def support():
    return

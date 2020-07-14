# djwc: Django WebComponents

## Introduction

WebComponents is a W3C standard supported by all browsers for a couple of years
now, see their [Getting Started](https://www.webcomponents.org/introduction)
introduction for details.

## Getting started

### How to try djwc

For a quick test:

- clone and enter this repo
- run `pip install django -e .`
- start the example with: `./manage.py djwc && ./manage.py runserver`

You should see some polymer components on `localhost:8000`

### How to install djwc

- `pip install djwc`,
- add `djwc` to `INSTALLED_APPS` (for the management command)
- add the `'djwc.middleware.StaticMiddleware'` `MIDDLEWARE` (to inject scripts).

### How to use webcomponents

- Declare the components that you want to use
- Run `./manage.py djwc` to install them (does not use NodeJS)
- Use the HTML tags for your components

That's **it** !! The middleware will do the rest.

Read on for details about each step.

## Declaring components

You can declare components per-app, per-project, and also include bundles.

### Settings

You can add a `paper-input` component to DJWC in the settings by referencing
its npm path:

```python
DJWC = {
    'COMPONENTS': {
        'paper-input': '@polymer/paper-input/paper-input.js',
    }
}
```

This will have predecence over any other setting.

### AppConfig

**Or**, define an `AppConfig.components` attribute to add components to your
reusable app.

```python
class AppConfig(apps.AppConfig):
    components = {
        'paper-input': '@polymer/paper-input/paper-input.js',
    }
```

This will be automatically detected.

### Libraries

You can also include a bunch of webcomponents with the `DJWC['LIBRARIES']`
setting:

```python
DJWC = {
    'LIBRARIES': ['djwc_polymer'],
}
```

More to come, these are manually maintained at this time.

## Installing components with `./manage.py djwc`

**Then**, run the `./manage.py djwc` command that will download all the scripts
into a static directory. Do this prior to collectstatic in production, and
every-time you change your components declaration.

## Using components

Just use your new tag wherever you want, such as in templates:

```html
<paper-input always-float-label label="Floating label"></paper-input>
```

The middleware will inject the corresponding script whenever the middleware
will find a `paper-input` tag.

## FAQ

### I've read that WebComponents are not accessible

Apparently, accessibility is [fine with aria
attributes](https://developer.salesforce.com/blogs/2020/01/accessibility-for-web-components.html).

### What next ?

- Do add unit tests when a contributor breaks it
- Optimize the djwc command
- Automate djwc_polymer
- Add moar bundles ! Like bootstrap-webcomponents ! yay !

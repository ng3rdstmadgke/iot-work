import click



CONTEXT_SETTINGS = {
    "help_option_names": ['-h', '--help']
}

# click.group: https://click.palletsprojects.com/en/8.1.x/commands/
@click.group(context_settings=CONTEXT_SETTINGS)
def cli():
    pass

#@cli.command()
#@click.argument("user_name", type=str)
#@click.option("-d", "--debug", default=False)
#def temp(user_name, debug):
#    pass

# click.options: https://click.palletsprojects.com/en/8.1.x/options/
@cli.command()
@click.option("-d", "--debug", default=False)
def temp(debug):
    from temp_sensor import temp
    temp.main()

if __name__ == "__main__":
    cli()

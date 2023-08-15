import click



CONTEXT_SETTINGS = {
    "help_option_names": ['-h', '--help']
}

# click.group: https://click.palletsprojects.com/en/8.1.x/commands/
@click.group(context_settings=CONTEXT_SETTINGS)
@click.option("-d", "--debug", default=False, is_flag=True)
@click.pass_context
def cli(context, debug):
    context.ensure_object(dict)
    context.obj["debug"] = debug

#@cli.command()
#@click.argument("user_name", type=str)
#@click.option("-d", "--debug", default=False)
#def temp(user_name, debug):
#    pass

# click.options: https://click.palletsprojects.com/en/8.1.x/options/
@cli.command()
@click.pass_context
@click.option("-cs", "--chip-select", default=0, type=int, help="ラズパイの CE0(0), CE1(1)どちらに接続するか")
@click.option("-ch", "--channel", default=0, type=int, help="MCP3002のCH0端子(0),CH1端子(1)どちらを利用するか")
def temp_wiringpi(context, chip_select, channel):
    from temp_sensor import temp_wiringpi
    temp_wiringpi.main(
        debug=context.obj["debug"],
        chip_select=chip_select,
        channel=channel,
    )

@cli.command()
@click.pass_context
@click.option("-cs", "--chip-select", default=0, type=int, help="ラズパイの CE0端子(0), CE1端子(1)どちらに接続するか")
@click.option("-ch", "--channel", default=0, type=int, help="MCP3002のCH0端子(0),CH1端子(1)どちらを利用するか")
def temp_pigpio(context, chip_select, channel):
    from temp_sensor import temp_pigpio
    temp_pigpio.main(
        debug=context.obj["debug"],
        chip_select=chip_select,
        channel=channel,
    )

@cli.command()
@click.pass_context
def display_counter(context):
    from display import counter
    counter.main()

@cli.command()
@click.pass_context
def display_temp_sensor(context):
    from display import temp_sensor
    temp_sensor.main()

if __name__ == "__main__":
    cli()

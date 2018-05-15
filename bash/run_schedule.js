'use strict';

const spawn = require('child_process').spawn;

const interval = setInterval(checkDate, 60000);

function checkDate() {
    const currentDate = new Date();
    if (currentDate.getDay() === 2 && currentDate.getHours() === 13 && currentDate.getMinutes() === 43) {
        console.log('Started Running the Script!');
        console.log(currentDate);
        runScript();
    }
}

function runScript() {
    const script = spawn('bash', [__dirname + '/run_planet.sh']);
    script.on('exit', () => {
        console.log('process exit');
    });
    script.stdout.pipe(process.stdout);:
    script.stderr.pipe(process.stderr);
}
runScript();

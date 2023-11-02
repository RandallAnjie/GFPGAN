const singUpBtn = document.querySelector('#sign-up-btn')
const singInBtn = document.querySelector('#sign-in-btn')
const container = document.querySelector('.container')

let countdownInterval;
let endTime;

let randomStr;
let fileName;

let thisInterval;

singUpBtn.addEventListener('click', () => {
	container.classList.add('sign-up-mode')
})
singInBtn.addEventListener('click', () => {
	container.classList.remove('sign-up-mode')
})


window.onload = function() {
	initialize();
	rShowMessage('网站全新上线～',0,'up', 5000);
	rShowMessage('你知道吗？我们的网站可以修复照片哦～<br />修复过程中不小心退出了？不要担心，我添加了历史记录回朔功能～<br />弹窗来自作者另一个开源项目<a href="https://notification.randallanjie.com/">R_Notification.js<br /></a>感谢使用～',0,'up', 0);
	// 等到8秒后，显示提示信息
	setTimeout(() => {
		rShowMessage('PS:这些消息可以右滑删除，左滑固定嗷～',0,'up', 5000);
		rShowMessage('你要是觉得修复时间太长，完全可以关掉浏览器，我们会在后台继续修复，半个小时之内打开本网站就会看到结果啦～>',0,'up', 5000);
	}, 8000);
	setTimeout(() => {
		rShowMessage('如果你想要下载修复后的图片，可以点击下载按钮哦～',0,'up', 5000);
	}, 16000);
	setTimeout(() => {
		rShowMessage('转接在这里祝您使用愉快～',0,'up', 5000);
	}, 24000);

};

function errorFunction(error) {
	localStorage.clear();
	// 清除randomStr和fileName中的值
	randomStr = null;
	fileName = null;
	console.error(error);
	document.getElementById('overlay').style.display = 'none'; // 隐藏灰色背景
	document.getElementById('overlay').style.zIndex = '0';
	// 弹窗显示错误信息
	rStatusMessage.error(error.message, '出错啦～');
}

async function huiFU() {
    try {
        // 开始轮询状态，直到处理完成
        const interval = setInterval(async () => {
            const queryResponse = await fetch(`/query?random_str=${randomStr}`);
			thisInterval = interval;

			if (queryResponse.status !== 200) {
				queryResponse.text().then(text => {
					const error = String(text);
					throw new Error(error);
				}).catch((error) => {
					clearInterval(interval); // 清除轮询定时器
					errorFunction(error);
				});
			}
			const queryData = await queryResponse.json();
            if (queryData.success) {
                // 处理完成后，显示处理前和处理后的图片，并添加下载按钮
                document.getElementById('input-image').src = `/download?random_str=${randomStr}&type=input&filename=${fileName}`;
                document.getElementById('output-image').src = `/download?random_str=${randomStr}&type=output&filename=${fileName}`;
                document.getElementById('download-link').href = `/download?random_str=${randomStr}&type=output&filename=${fileName}`;
                document.getElementById('input-form').style.display = 'none';
                document.getElementById('result').style.display = 'inline-block';

                clearInterval(interval); // 清除轮询定时器
                document.getElementById('overlay').style.display = 'none'; // 隐藏灰色背景
                document.getElementById('overlay').style.zIndex = '0';
            }
        }, 1000); // 定时1秒钟查询一次
    } catch (error) {
		errorFunction(error);
    }
}

function clearLocalStorage() {
	localStorage.clear();
	// 清除randomStr和fileName中的值
	randomStr = null;
	fileName = null;
	rShowMessage('前台清除成功～如果照片没有修复完成那么照片将在后台持续进行，您可以选择与转接联系去拿到图片～感谢使用～～～', 0, 'up', 4000);
	// 清楚jquery定时器
	clearInterval(thisInterval); // 清除轮询定时器
	initialize();
}


function initialize() {
	if (localStorage.getItem("randomStr") !== null && localStorage.getItem("fileName") !== null) {
		randomStr = localStorage.getItem("randomStr");
		fileName = localStorage.getItem("fileName");
		// 隐藏result容器
		document.getElementById('result').style.display = 'none';

		document.getElementById("timer").innerHTML = "正在恢复上次修复的照片，请稍候～";

		// 背景和loading
		document.getElementById('overlay').style.display = 'block';
		document.getElementById('overlay').style.zIndex = '9988';

		try {
			huiFU();
		} catch (error) {
			errorFunction(error);
		}
	} else {
		localStorage.clear();
		// 隐藏result容器
		document.getElementById('result').style.display = 'none';
		// 隐藏loading
		document.getElementById('overlay').style.display = 'none';
		// 显示input表单
		document.getElementById('input-form').style.display = 'flex';
	}
}

fetch('/tongji')
	.then(response => response.json())
	.then(data => {
		const number = data;
		const numberDisplay = document.getElementById('numberDisplay');
		numberDisplay.textContent = number;
	})
	.catch(error => {
		console.error('Error fetching number:', error);
	});

function startCountDown(inputSeconds) {
	clearInterval(countdownInterval); // Clear any existing intervals
 	endTime = new Date().getTime() + inputSeconds * 1000;
	 updateCountdown();
	 countdownInterval = setInterval(updateCountdown, 1000);
}

function updateCountdown() {
	const currentTime = new Date().getTime();
	const remainingTime = endTime - currentTime;
	if (remainingTime <= 0) {
		 document.getElementById("timer").innerHTML = "已超出预期时间,五分钟之内都属于正常时间,请耐心等待～";
		 clearInterval(countdownInterval);
	} else {
		const minutes = Math.floor((remainingTime % (1000 * 60 * 60)) / (1000 * 60));
		const seconds = Math.floor((remainingTime % (1000 * 60)) / 1000);

		document.getElementById("timer").innerHTML = "请耐心等待，预计处理剩余时间："+('0' + minutes).slice(-2) + ":" + ('0' + seconds).slice(-2);
	}
}

document.addEventListener('DOMContentLoaded', function() {
	document.getElementById('submit-btn')
		.addEventListener('click', function() {
			// 隐藏result容器
			document.getElementById('result').style.display = 'none';
			// 背景和loading
			document.getElementById('overlay').style.display = 'block';
			document.getElementById('overlay').style.zIndex = '9988';

			// 获取选中的文件和版本号
			const fileInput = document.getElementById('file-input');
			const version = document.getElementById('version').value;
			const upscale = document.getElementById('upscale-input').value;

			// 创建一个FormData对象，并添加文件和版本信息
			const formData = new FormData();
			formData.append('file', fileInput.files[0]);
			formData.append('version', version);
			formData.append('upscale', upscale);


			fetch('/upload', {
					method: 'POST',
					body: formData,
				})
				.then((response) => {
					if (!response.ok) {
						return response.text().then((errorText) => {
							throw new Error(errorText);
						});
					}else{
						return response.text();
					}
				})
				.then((random_str) => {
					randomStr = random_str
					fileName = encodeURIComponent(fileInput.files[0].name)
					localStorage.setItem("randomStr", randomStr);
            		localStorage.setItem("fileName", fileName);
					const response =  fetch(`/gettime?random_str=${randomStr}&file_name=${fileName}`)
						.then((response) => response.json())
						.then((data) => {
							const inputSeconds = data.seconds;
							startCountDown(inputSeconds);
						});
					// 开始轮询状态，直到处理完成
					const interval = setInterval(() => {
						fetch(`/query?random_str=${randomStr}`)
							.then((response) => response.json())
							.then((data) => {
								if (data.success) {
									// 处理完成后，显示处理前和处理后的图片，并添加下载按钮
									document.getElementById('input-image').src = `/download?random_str=${randomStr}&type=input&filename=${fileName}`;
									document.getElementById('output-image').src = `/download?random_str=${randomStr}&type=output&filename=${fileName}`;
									document.getElementById('download-link').href = `/download?random_str=${randomStr}&type=output&filename=${fileName}`;
									document.getElementById('input-form').style.display = 'none';
									document.getElementById('result').style.display = 'inline-block';

									clearInterval(interval); // 清除轮询定时器
									document.getElementById('overlay').style.display = 'none'; // 隐藏灰色背景
									document.getElementById('overlay').style.zIndex = '0';
								}
							});
					}, 1000); // 定时1秒钟查询一次
				})
				.catch((error) => {
					errorFunction(error);
				});
		});
});